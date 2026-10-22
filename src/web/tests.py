"""Tests for the WhatsApp view-only (parent) access flow."""
import json
import tempfile
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from children.models import Child, Circle, Member
from elearning.models import Cohort, Course, CourseRun, Lesson, Module
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
        for path in ("/messages/", "/urgent-alerts/", "/elearning/courses/"):
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
        for path in ("/messages/", "/urgent-alerts/", "/elearning/courses/"):
            resp = self.client.get(path)
            self.assertEqual(resp.status_code, 200, f"staff blocked from {path}")


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class UpdatePhotoUploadTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff2", password="x")
        self.staff.groups.add(Group.objects.get_or_create(name="staff")[0])
        self.client.force_login(self.staff)
        self.child = Child.objects.create(name="Ada")

    def test_upload_creates_linked_photos(self):
        from updates.models import Update

        img = SimpleUploadedFile("a.jpg", b"\xff\xd8\xff\xe0fake", content_type="image/jpeg")
        resp = self.client.post(
            "/updates/create/",
            {"child": self.child.id, "text": "first day", "photos": img},
        )
        self.assertEqual(resp.status_code, 302)

        update = Update.objects.get(child=self.child)
        self.assertEqual(update.photos.count(), 1)
        # The generic owner FK resolves back to the update.
        self.assertEqual(update.photos.first().owner, update)


class CourseRunAndOrderTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin4", password="x")
        self.admin.groups.add(Group.objects.get_or_create(name="staff")[0])
        self.client.force_login(self.admin)
        self.course_a = Course.objects.create(title="A")
        self.course_b = Course.objects.create(title="B")
        self.cohort = Cohort.objects.create(name="C1")

    def _post(self, path, payload):
        return self.client.post(
            path, data=json.dumps(payload), content_type="application/json"
        )

    def test_new_run_deactivates_previous(self):
        old = CourseRun.objects.create(
            cohort=self.cohort, course=self.course_a, start_date="2026-09-01"
        )
        resp = self._post(
            f"/elearning/cohorts/{self.cohort.pk}/runs/create/",
            {"course": self.course_b.pk, "start_date": "2026-10-01", "send_hour": 9},
        )
        self.assertEqual(resp.status_code, 302)
        old.refresh_from_db()
        self.assertFalse(old.active)
        active = CourseRun.objects.get(active=True)
        self.assertEqual((active.course, active.send_hour), (self.course_b, 9))

    def test_run_without_start_date_is_rejected(self):
        resp = self._post(
            f"/elearning/cohorts/{self.cohort.pk}/runs/create/",
            {"course": self.course_a.pk},
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(CourseRun.objects.exists())

    def test_new_module_goes_after_highest_order(self):
        Module.objects.create(course=self.course_a, title="m0", order=0)
        m1 = Module.objects.create(course=self.course_a, title="m1", order=1)
        Module.objects.create(course=self.course_a, title="m2", order=2)
        self._post(f"/elearning/modules/{m1.pk}/delete/", {})
        self._post("/elearning/modules/create/", {"course": self.course_a.pk, "title": "m3"})
        self.assertEqual(Module.objects.get(title="m3").order, 3)

    def test_new_lesson_goes_after_highest_order(self):
        module = Module.objects.create(course=self.course_a, title="m", order=0)
        Lesson.objects.create(module=module, title="l0", youtube_url="u", order=0)
        l1 = Lesson.objects.create(module=module, title="l1", youtube_url="u", order=1)
        Lesson.objects.create(module=module, title="l2", youtube_url="u", order=2)
        self._post(f"/elearning/lessons/{l1.pk}/delete/", {})
        self._post(
            "/elearning/lessons/create/",
            {"module": module.pk, "title": "l3", "youtube_url": "u"},
        )
        self.assertEqual(Lesson.objects.get(title="l3").order, 3)
