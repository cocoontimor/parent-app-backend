"""Tests for digest-level acknowledgment attribution on announcements."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from announcements.models import Announcement
from announcements.serializers import AnnouncementSerializer
from messaging.models import MessageLog
from messaging.services import ACK_PAYLOAD_PREFIX, record_acknowledgment
from messaging.tasks import send_daily_digest

User = get_user_model()


class AnnouncementDigestAckTests(TestCase):
    def setUp(self):
        self.parent_group, _ = Group.objects.get_or_create(name="parent")
        self.staff = User.objects.create_user(username="admin", is_staff=True)
        self.parent = User.objects.create_user(username="6591111111")
        self.parent.groups.add(self.parent_group)

    def test_digest_ack_attributed_to_announcement(self):
        from messaging.services import queue_announcement_for_digest

        # No circles -> goes to all parents.
        ann = Announcement.objects.create(title="T", body="B", created_by=self.staff)
        queue_announcement_for_digest(ann)

        send_daily_digest()  # composes + "sends" the digest, links DigestQueue rows

        # Before the parent acks, the announcement counts one recipient, zero acks.
        data = AnnouncementSerializer(ann).data
        self.assertEqual(data["recipient_count"], 1)
        self.assertEqual(data["ack_count"], 0)

        # Simulate the parent tapping the digest's acknowledge button.
        log = MessageLog.objects.get(recipient=self.parent, template="daily_digest")
        record_acknowledgment("6591111111", f"{ACK_PAYLOAD_PREFIX}{log.id}")

        data = AnnouncementSerializer(ann).data
        self.assertEqual(data["ack_count"], 1)
