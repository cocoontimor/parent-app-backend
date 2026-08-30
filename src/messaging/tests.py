"""Tests for the WhatsApp keyword -> magic-link reply."""
import hashlib
import hmac
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from messaging.views import _maybe_send_app_link, _valid_signature
from web.tokens import resolve_login_token

User = get_user_model()


class PeriodicTaskFixtureTests(TestCase):
    def test_fixture_loads_expected_schedule(self):
        from django.core.management import call_command
        from django_celery_beat.models import PeriodicTask

        # Migration 0004 already seeded the tasks; loading the fixture on top
        # must reassert the same two rows without creating duplicates.
        call_command("loaddata", "periodic_tasks", verbosity=0)

        tasks = {t.name: t for t in PeriodicTask.objects.all()}
        self.assertEqual(
            set(tasks), {"send-daily-digest", "release-due-lessons"}
        )
        self.assertEqual(PeriodicTask.objects.count(), 2)

        digest = tasks["send-daily-digest"]
        self.assertEqual(digest.task, "messaging.tasks.send_daily_digest")
        self.assertEqual((digest.crontab.hour, digest.crontab.minute), ("15", "0"))
        self.assertEqual(str(digest.crontab.timezone), "Asia/Dili")

        lessons = tasks["release-due-lessons"]
        self.assertEqual(lessons.task, "elearning.tasks.release_due_lessons")
        # Runs hourly; the per-cohort send_hour decides actual delivery time.
        self.assertEqual((lessons.crontab.hour, lessons.crontab.minute), ("*", "0"))


class WebhookSignatureTests(TestCase):
    def _post(self, body=b"{}", signature=None):
        headers = {}
        if signature is not None:
            headers["HTTP_X_HUB_SIGNATURE_256"] = signature
        return RequestFactory().post(
            "/webhooks/whatsapp/",
            data=body,
            content_type="application/json",
            **headers,
        )

    def _sign(self, secret, body):
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    @override_settings(WHATSAPP_APP_SECRET="", DEBUG=True)
    def test_missing_secret_allowed_in_debug(self):
        self.assertTrue(_valid_signature(self._post()))

    @override_settings(WHATSAPP_APP_SECRET="", DEBUG=False)
    def test_missing_secret_rejected_in_production(self):
        # The fix: never process an unverified webhook in production.
        self.assertFalse(_valid_signature(self._post()))

    @override_settings(WHATSAPP_APP_SECRET="s3cret", DEBUG=False)
    def test_valid_signature_accepted(self):
        body = b'{"hello":"world"}'
        req = self._post(body=body, signature=self._sign("s3cret", body))
        self.assertTrue(_valid_signature(req))

    @override_settings(WHATSAPP_APP_SECRET="s3cret", DEBUG=False)
    def test_wrong_signature_rejected(self):
        req = self._post(body=b'{"hello":"world"}', signature="sha256=deadbeef")
        self.assertFalse(_valid_signature(req))

    @override_settings(WHATSAPP_APP_SECRET="s3cret", DEBUG=False)
    def test_missing_signature_header_rejected(self):
        self.assertFalse(_valid_signature(self._post(body=b"{}")))


class AppLinkReplyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="6591234567")

    @mock.patch("messaging.services.send_text_message")
    def test_keyword_from_known_user_sends_link(self, send):
        _maybe_send_app_link("6591234567", "menu")
        self.assertTrue(send.called)
        phone, text = send.call_args.args
        self.assertEqual(phone, "6591234567")
        self.assertIn("/m/", text)
        # The link's token resolves back to the same user.
        token = text.split("/m/")[1].split("/")[0]
        self.assertEqual(resolve_login_token(token), self.user)

    @mock.patch("messaging.services.send_text_message")
    def test_non_keyword_ignored(self, send):
        _maybe_send_app_link("6591234567", "thanks!")
        self.assertFalse(send.called)

    @mock.patch("messaging.services.send_text_message")
    def test_unknown_number_ignored(self, send):
        _maybe_send_app_link("6500000000", "menu")
        self.assertFalse(send.called)


class UrgentAlertSendTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import Group

        self.parent_group, _ = Group.objects.get_or_create(name="parent")
        self.staff = User.objects.create_user(username="admin", is_staff=True)

    def _make_parent(self, phone, *, graduated):
        from children.models import Child, Circle, Member

        parent = User.objects.create_user(username=phone)
        parent.groups.add(self.parent_group)
        child = Child.objects.create(name=f"child-{phone}", graduated=graduated)
        circle = Circle.objects.create(name=f"fam-{phone}", type=Circle.Type.FAMILY)
        circle.children.add(child)
        Member.objects.create(
            user=parent, circle=circle, relationship=Member.Relationship.MOTHER
        )
        return parent

    def test_skips_parents_of_only_graduated_children(self):
        from messaging.models import MessageLog
        from messaging.tasks import send_urgent_alert
        from updates.models import UrgentAlert

        self._make_parent("6591111111", graduated=False)
        self._make_parent("6592222222", graduated=True)  # graduated -> skipped
        alert = UrgentAlert.objects.create(title="T", body="B", created_by=self.staff)

        send_urgent_alert(alert.id)

        recipients = set(MessageLog.objects.values_list("recipient__username", flat=True))
        self.assertEqual(recipients, {"6591111111"})

    def test_ack_reporting_per_alert(self):
        from django.db.models import Count, Q

        from messaging.models import MessageLog
        from messaging.services import ACK_PAYLOAD_PREFIX, record_acknowledgment
        from messaging.tasks import send_urgent_alert
        from updates.models import UrgentAlert

        parent = self._make_parent("6591111111", graduated=False)
        alert = UrgentAlert.objects.create(title="T", body="B", created_by=self.staff)
        send_urgent_alert(alert.id)

        log = MessageLog.objects.get(recipient=parent)
        self.assertEqual(log.source, alert)  # linked via the generic source FK

        # Simulate the parent tapping the acknowledge quick-reply button.
        record_acknowledgment("6591111111", f"{ACK_PAYLOAD_PREFIX}{log.id}")

        annotated = UrgentAlert.objects.annotate(
            recipient_count=Count("message_logs", distinct=True),
            ack_count=Count(
                "message_logs",
                filter=Q(message_logs__acknowledged_at__isnull=False),
                distinct=True,
            ),
        ).get(id=alert.id)
        self.assertEqual(annotated.recipient_count, 1)
        self.assertEqual(annotated.ack_count, 1)
