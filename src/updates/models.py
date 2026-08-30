from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from utils.models import BaseModel


class Update(BaseModel):
    child = models.ForeignKey(
        "children.Child",
        on_delete=models.CASCADE,
        related_name="updates",
    )
    text = models.TextField()
    photos = GenericRelation(
        "photos.Photo",
        content_type_field="owner_type",
        object_id_field="owner_id",
        related_query_name="update",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_updates",
    )

    class Meta:
        db_table = "updates"
        ordering = ["-created"]

    def __str__(self):
        return f"Update for {self.child.name}"


class UrgentAlert(BaseModel):
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="urgent_alerts",
    )
    # Messages sent for this alert, linked via MessageLog's generic source FK.
    # Reverse accessor for annotating recipient/ack counts per alert.
    message_logs = GenericRelation(
        "messaging.MessageLog",
        content_type_field="source_type",
        object_id_field="source_id",
        related_query_name="urgent_alert",
    )

    class Meta:
        db_table = "urgent_alerts"
        ordering = ["-created"]

    def __str__(self):
        return self.title
