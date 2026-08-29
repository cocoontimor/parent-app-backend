from django.conf import settings
from django.db import models

from utils.models import BaseModel


class Announcement(BaseModel):
    title = models.CharField(max_length=255)
    body = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements",
    )
    circles = models.ManyToManyField(
        "children.Circle",
        related_name="announcements",
        blank=True,
    )

    class Meta:
        db_table = "announcements"
        ordering = ["-created"]

    def __str__(self):
        return self.title

    def get_recipient_parents(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        parents = User.objects.filter(groups__name="parent")

        if self.circles.exists():
            return parents.filter(
                circles__in=self.circles.all(),
            ).distinct()
        return parents


def announcement_photo_upload_path(instance, filename):
    return f"announcements/{instance.announcement_id}/photos/{filename}"


class AnnouncementPhoto(BaseModel):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    image = models.ImageField(upload_to=announcement_photo_upload_path)

    class Meta:
        db_table = "announcement_photos"
        ordering = ["created"]

    def __str__(self):
        return f"Photo for {self.announcement_id}"


class AnnouncementAck(BaseModel):
    announcement = models.ForeignKey(
        Announcement,
        on_delete=models.CASCADE,
        related_name="acks",
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcement_acks",
    )

    class Meta:
        db_table = "announcement_acks"
        unique_together = [("announcement", "parent")]

    def __str__(self):
        return f"{self.parent} ack {self.announcement}"
