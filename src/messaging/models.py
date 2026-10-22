from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from utils.models import BaseModel


class MessageLog(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        READ = "read", "Read"
        FAILED = "failed", "Failed"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="message_logs",
    )
    template = models.CharField(max_length=100, blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    # WhatsApp's own message id, returned on send. Lets delivery/read receipts
    # target this exact message instead of every message to the same phone.
    wa_message_id = models.CharField(max_length=128, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    # Set when the recipient taps the message's acknowledge quick-reply button.
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)
    # Optional link to the object this message was sent for (e.g. an UrgentAlert
    # or Announcement), so acknowledgments can be reported per source. object_id
    # is a CharField to match the app's ULID primary keys.
    source_type = models.ForeignKey(
        ContentType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    source_id = models.CharField(max_length=26, null=True, blank=True, db_index=True)
    source = GenericForeignKey("source_type", "source_id")

    class Meta:
        db_table = "message_logs"
        ordering = ["-created"]

    def __str__(self):
        return f"Message to {self.recipient} [{self.status}]"


class InboundMessage(BaseModel):
    """A message received from a parent via the WhatsApp webhook."""

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inbound_messages",
    )
    from_phone = models.CharField(max_length=20)
    wa_message_id = models.CharField(max_length=128, unique=True)
    message_type = models.CharField(max_length=20, blank=True)
    text = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "inbound_messages"
        ordering = ["-created"]

    def __str__(self):
        return f"Inbound {self.message_type} from {self.from_phone}"


class DigestQueue(BaseModel):
    class ItemType(models.TextChoices):
        ANNOUNCEMENT = "announcement", "Announcement"
        UPDATE = "update", "Update"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="digest_items",
    )
    item_type = models.CharField(max_length=15, choices=ItemType.choices)
    item_id = models.CharField(max_length=26)
    processed = models.BooleanField(default=False)
    # The message that delivered this item, set when the digest is sent. Lets a
    # digest ack (MessageLog.acknowledged_at) be attributed back to each item it
    # bundled — e.g. per-announcement ack counts.
    message_log = models.ForeignKey(
        "MessageLog",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="digest_items",
    )

    class Meta:
        db_table = "digest_queue"
        ordering = ["created"]

    def __str__(self):
        return f"{self.item_type}:{self.item_id} for {self.recipient}"
