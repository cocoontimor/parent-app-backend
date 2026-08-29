"""Tests for the WhatsApp view-only (parent) access flow."""
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from children.models import Child, Circle, Member
from payments.models import FeePayment
from web.tokens import make_login_token, resolve_login_token

User = get_user_model()


def _make_parent(phone, child_name):
    """A parent user + their own child in a family circle, plus a fee payment."""
    parent = User.objects.create_user(username=phone)
    parent.groups.add(Group.objects.get_or_create(name="parent")[0])
    child = Child.objects.create(name=child_name)
    circle = Circle.objects.create(name=f"{child_name} family", type=Circle.Type.FAMILY)
    circle.children.add(child)
    Member.objects.create(user=parent, circle=circle, relationship=Member.Relationship.MOTHER)
    return parent, child


class LoginTokenTests(TestCase):
    def test_round_trip(self):
        user = User.objects.create_user(username="6591234567")
        token = make_login_token(user)
        self.assertEqual(resolve_login_token(token), user)

    def test_expired(self):
        user = User.objects.create_user(username="6591234567")
        token = make_login_token(user)
        # max_age=-1 forces the token to read as already expired.
        self.assertIsNone(resolve_login_token(token, max_age=-1))

    def test_tampered(self):
        user = User.objects.create_user(username="6591234567")
        token = make_login_token(user) + "x"
        self.assertIsNone(resolve_login_token(token))


class MagicLoginViewTests(TestCase):
    def test_valid_token_logs_in(self):
        parent, _ = _make_parent("6591234567", "Ada")
        resp = self.client.get(f"/m/{make_login_token(parent)}/")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, "/")
        self.assertEqual(self.client.session["_auth_user_id"], str(parent.pk))

    def test_invalid_token_shows_login(self):
        resp = self.client.get("/m/not-a-real-token/")
        self.assertEqual(resp.status_code, 200)  # re-renders Auth/Login
        self.assertNotIn("_auth_user_id", self.client.session)


class ParentAccessTests(TestCase):
    def setUp(self):
        self.parent, self.child = _make_parent("6591234567", "Ada")
        # A second family the parent has nothing to do with.
        _other_parent, other_child = _make_parent("6599999999", "Zed")
        FeePayment.objects.create(child=self.child, month="2026-08", amount=Decimal("100"))
        FeePayment.objects.create(child=other_child, month="1999-01", amount=Decimal("200"))
        self.client.force_login(self.parent)

    def test_payments_scoped_to_own_children(self):
        resp = self.client.get("/payments/")
        content = resp.content.decode()
        self.assertIn("2026-08", content)       # own child's payment present
        self.assertNotIn("1999-01", content)    # other family's payment absent
        self.assertNotIn("Zed", content)

    def test_staff_only_pages_denied(self):
        for path in ("/messages/", "/urgent-alerts/", "/elearning/"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 302, f"{path} should redirect parents")
            self.assertEqual(resp.url, "/")

    def test_cannot_open_another_familys_child(self):
        _op, other_child = _make_parent("6588888888", "Kai")
        resp = self.client.get(f"/children/{other_child.pk}/")
        self.assertEqual(resp.status_code, 404)


class StaffAccessTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff1", password="x")
        self.staff.groups.add(Group.objects.get_or_create(name="staff")[0])
        self.client.force_login(self.staff)

    def test_staff_reach_admin_pages(self):
        for path in ("/messages/", "/urgent-alerts/", "/elearning/"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"staff blocked from {path}")
