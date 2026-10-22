"""Tests for the WhatsApp view-only (parent) access flow."""
import json
import tempfile
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from announcements.models import Announcement
from attendance.models import Attendance
from children.models import Child, Circle, Member
from elearning.models import Cohort, Course, CourseRun, Lesson, Module
from payments.models import FeePayment
from updates.models import Update
from users.serializers import UserSerializer
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


def _make_teacher_class(username, class_name, child_names):
    """A teacher + a classroom they teach + its children."""
    teacher = User.objects.create_user(username=username)
    teacher.groups.add(Group.objects.get_or_create(name="teacher")[0])
    circle = Circle.objects.create(name=class_name, type=Circle.Type.CLASSROOM)
    Member.objects.create(
        user=teacher, circle=circle, relationship=Member.Relationship.TEACHER
    )
    children = []
    for n in child_names:
        c = Child.objects.create(name=n)
        circle.children.add(c)
        children.append(c)
    return teacher, circle, children


class TeacherAccessTests(TestCase):
    def setUp(self):
        self.t1, self.c1, self.kids1 = _make_teacher_class("t1", "Room A", ["Ann", "Bob"])
        self.t2, self.c2, self.kids2 = _make_teacher_class("t2", "Room B", ["Cara"])
        self.client.force_login(self.t1)

    def test_children_span_all_classes(self):
        Child.objects.create(name="Dina")  # not in any classroom
        content = self.client.get("/children/").content.decode()
        self.assertIn("Ann", content)          # own class child present
        self.assertIn("Cara", content)         # other class child present
        self.assertNotIn("Dina", content)      # unassigned child absent

    def test_can_open_other_class_child(self):
        resp = self.client.get(f"/children/{self.kids2[0].pk}/")
        self.assertEqual(resp.status_code, 200)

    def test_can_edit_own_child(self):
        resp = self.client.post(f"/children/{self.kids1[0].pk}/edit/", {"name": "Annie"})
        self.assertEqual(resp.status_code, 302)
        self.kids1[0].refresh_from_db()
        self.assertEqual(self.kids1[0].name, "Annie")

    def test_can_edit_other_class_child(self):
        resp = self.client.post(f"/children/{self.kids2[0].pk}/edit/", {"name": "Carla"})
        self.assertEqual(resp.status_code, 302)
        self.kids2[0].refresh_from_db()
        self.assertEqual(self.kids2[0].name, "Carla")

    def test_can_mark_own_class_attendance(self):
        resp = self.client.post(
            f"/classes/{self.c1.pk}/attendance/save/",
            data=json.dumps(
                {"date": "2026-08-31", "roster": [{"id": self.kids1[0].pk, "status": "absent"}]}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 302)

    def test_can_mark_other_class_attendance(self):
        resp = self.client.post(
            f"/classes/{self.c2.pk}/attendance/save/",
            data=json.dumps({"date": "2026-08-31", "roster": []}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 302)

    def test_cannot_create_class(self):
        resp = self.client.post(
            "/classes/create/",
            data=json.dumps({"name": "Sneaky"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)

    def test_can_announce_to_own_class(self):
        resp = self.client.post(
            "/announcements/create/",
            {"title": "Hi", "body": "Room A news", "circles": [self.c1.pk]},
        )
        self.assertEqual(resp.status_code, 302)
        a = Announcement.objects.get(title="Hi")
        self.assertEqual(list(a.circles.values_list("pk", flat=True)), [self.c1.pk])

    def test_cannot_announce_to_all_parents(self):
        resp = self.client.post(
            "/announcements/create/", {"title": "Broadcast", "body": "x"}  # no circles
        )
        self.assertEqual(resp.status_code, 403)

    def test_can_announce_to_other_class(self):
        resp = self.client.post(
            "/announcements/create/",
            {"title": "Room B", "body": "x", "circles": [self.c2.pk]},
        )
        self.assertEqual(resp.status_code, 302)


class PaymentLedgerTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin1", password="x")
        self.admin.groups.add(Group.objects.get_or_create(name="staff")[0])
        self.t1, self.c1, self.kids1 = _make_teacher_class("pt1", "Room A", ["Ann", "Bob"])
        self.t2, self.c2, self.kids2 = _make_teacher_class("pt2", "Room B", ["Cara"])

    def _post(self, path, payload):
        return self.client.post(
            path, data=json.dumps(payload), content_type="application/json"
        )

    def test_admin_generate_creates_pending_and_is_idempotent(self):
        self.client.force_login(self.admin)
        resp = self._post("/payments/generate/", {"month": "2026-09", "amount": "50"})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            FeePayment.objects.filter(month="2026-09", status="pending").count(), 3
        )
        # Re-running creates nothing (unique per child+month).
        self._post("/payments/generate/", {"month": "2026-09", "amount": "50"})
        self.assertEqual(FeePayment.objects.filter(month="2026-09").count(), 3)

    def test_generate_skips_graduated(self):
        self.kids1[0].graduation_date = date(2026, 1, 1)
        self.kids1[0].save()
        self.client.force_login(self.admin)
        self._post("/payments/generate/", {"month": "2026-09", "amount": "50"})
        self.assertEqual(FeePayment.objects.filter(month="2026-09").count(), 2)

    def test_teacher_cannot_generate(self):
        self.client.force_login(self.t1)
        resp = self._post("/payments/generate/", {"month": "2026-09", "amount": "50"})
        self.assertEqual(resp.status_code, 403)

    @mock.patch("web.views.send_payment_confirmation")
    def test_mark_paid_sends_receipt(self, send):
        inv = FeePayment.objects.create(
            child=self.kids1[0], month="2026-09", amount=50, status="pending"
        )
        self.client.force_login(self.t1)
        resp = self._post(f"/payments/{inv.pk}/mark/", {"status": "paid"})
        self.assertEqual(resp.status_code, 302)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "paid")
        self.assertIsNotNone(inv.paid_at)
        self.assertEqual(inv.marked_by, self.t1)
        send.assert_called_once_with(inv)

    @mock.patch("web.views.send_payment_confirmation")
    def test_mark_paid_again_does_not_resend(self, send):
        inv = FeePayment.objects.create(
            child=self.kids1[0], month="2026-09", amount=50, status="paid"
        )
        self.client.force_login(self.t1)
        self._post(f"/payments/{inv.pk}/mark/", {"status": "paid"})
        send.assert_not_called()

    @mock.patch("web.views.send_payment_confirmation")
    def test_waive_sets_status_no_send(self, send):
        inv = FeePayment.objects.create(
            child=self.kids1[0], month="2026-09", amount=50, status="pending"
        )
        self.client.force_login(self.t1)
        self._post(f"/payments/{inv.pk}/mark/", {"status": "waived"})
        inv.refresh_from_db()
        self.assertEqual(inv.status, "waived")
        self.assertIsNone(inv.paid_at)
        send.assert_not_called()

    @mock.patch("web.views.send_payment_confirmation")
    def test_teacher_can_mark_other_class(self, send):
        # Teachers swap rooms to cover staffing, so any classroom is theirs.
        inv = FeePayment.objects.create(
            child=self.kids2[0], month="2026-09", amount=50, status="pending"
        )
        self.client.force_login(self.t1)  # Room A teacher, inv is Room B
        resp = self._post(f"/payments/{inv.pk}/mark/", {"status": "paid"})
        self.assertEqual(resp.status_code, 302)
        inv.refresh_from_db()
        self.assertEqual(inv.status, "paid")


class UserCreateTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin2", password="x")
        self.admin.groups.add(Group.objects.get_or_create(name="staff")[0])
        self.client.force_login(self.admin)

    def test_create_teacher_is_password_based_and_grouped(self):
        resp = self.client.post(
            "/users/create/",
            data=json.dumps(
                {"role": "teacher", "username": "sr.rosa", "full_name": "Sr Rosa", "password": "pw"}
            ),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(username="sr.rosa")
        self.assertIn("teacher", set(u.groups.values_list("name", flat=True)))
        self.assertTrue(u.has_usable_password())

    def test_teacher_reports_teacher_role(self):
        t, _, _ = _make_teacher_class("roleteach", "Room Z", [])
        self.assertEqual(UserSerializer(t).data["role"], "teacher")


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


class ReviewFixTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin3", password="x")
        self.admin.groups.add(Group.objects.get_or_create(name="staff")[0])
        self.t1, self.c1, self.kids1 = _make_teacher_class("rt1", "Room A", ["Ann"])

    def _post(self, path, payload):
        return self.client.post(
            path, data=json.dumps(payload), content_type="application/json"
        )

    def test_teacher_can_open_announcement(self):
        a = Announcement.objects.create(title="Hi", body="x", created_by=self.admin)
        a.circles.set([self.c1])
        self.client.force_login(self.t1)
        self.assertEqual(self.client.get(f"/announcements/{a.pk}/").status_code, 200)

    def test_parent_can_open_center_wide_announcement(self):
        parent, _ = _make_parent("67077770000", "Pia")
        a = Announcement.objects.create(title="All", body="x", created_by=self.admin)
        self.client.force_login(parent)
        self.assertEqual(self.client.get(f"/announcements/{a.pk}/").status_code, 200)

    def test_mark_rejects_backslash_redirect(self):
        inv = FeePayment.objects.create(
            child=self.kids1[0], month="2026-09", amount=50, status="paid"
        )
        self.client.force_login(self.admin)
        resp = self._post(
            f"/payments/{inv.pk}/mark/", {"status": "waived", "next": "/\\\\evil.example/"}
        )
        self.assertEqual(resp["Location"], f"/children/{self.kids1[0].pk}/")

    def test_mark_keeps_internal_redirect(self):
        inv = FeePayment.objects.create(
            child=self.kids1[0], month="2026-09", amount=50, status="paid"
        )
        self.client.force_login(self.admin)
        resp = self._post(
            f"/payments/{inv.pk}/mark/", {"status": "waived", "next": "/payments/?month=2026-09"}
        )
        self.assertEqual(resp["Location"], "/payments/?month=2026-09")

    @mock.patch("django.utils.timezone.now")
    def test_attendance_defaults_to_dili_date(self, now):
        # 23:00 UTC on the 1st is 08:00 on the 2nd in Dili (UTC+9).
        now.return_value = datetime(2026, 9, 1, 23, 0, tzinfo=dt_timezone.utc)
        self.client.force_login(self.t1)
        resp = self.client.get(
            f"/classes/{self.c1.pk}/attendance/", HTTP_X_INERTIA="true"
        )
        self.assertEqual(resp.json()["props"]["date"], "2026-09-02")

    def test_attendance_invalid_date_is_not_a_500(self):
        self.client.force_login(self.t1)
        resp = self.client.get(f"/classes/{self.c1.pk}/attendance/?date=2026-13-40")
        self.assertEqual(resp.status_code, 200)
        resp = self._post(
            f"/classes/{self.c1.pk}/attendance/save/", {"date": "2026-13-40", "roster": []}
        )
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Attendance.objects.exists())

    def test_class_picker_lists_teacher_role_users(self):
        self.client.force_login(self.admin)
        resp = self.client.get("/classes/", HTTP_X_INERTIA="true")
        names = {u["username"] for u in resp.json()["props"]["users"]}
        self.assertIn("rt1", names)

    def test_class_update_keeps_teachers_and_ignores_parents(self):
        parent, _ = _make_parent("67077770001", "Pia")
        self.client.force_login(self.admin)
        self._post(
            f"/classes/{self.c1.pk}/edit/",
            {"name": "Room A", "members": [self.t1.pk, parent.pk], "children": []},
        )
        self.assertEqual(
            list(self.c1.member_records.values_list("user_id", flat=True)), [self.t1.pk]
        )

    def test_users_create_error_keeps_user_list(self):
        self.client.force_login(self.admin)
        resp = self.client.post(
            "/users/create/",
            {"role": "teacher", "username": "rt1", "password": "x"},
            HTTP_X_INERTIA="true",
        )
        props = resp.json()["props"]
        self.assertIn("username", props["errors"])
        self.assertIn("rt1", {u["username"] for u in props["users"]})


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
