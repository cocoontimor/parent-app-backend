from django.conf import settings
from django.db import models

from utils.models import BaseModel


class MessageLog(BaseModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
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
    sent_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "message_logs"
        ordering = ["-created"]

    def __str__(self):
        return f"Message to {self.recipient} [{self.status}]"


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

    class Meta:
        db_table = "digest_queue"
        ordering = ["created"]

    def __str__(self):
        return f"{self.item_type}:{self.item_id} for {self.recipient}"
