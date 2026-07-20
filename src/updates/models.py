from django.conf import settings
from django.db import models

from utils.models import BaseModel


class Update(BaseModel):
    child = models.ForeignKey(
        "children.Child",
        on_delete=models.CASCADE,
        related_name="updates",
    )
    text = models.TextField()
    photo = models.ImageField(upload_to="updates/photos/", blank=True)
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

    class Meta:
        db_table = "urgent_alerts"
        ordering = ["-created"]

    def __str__(self):
        return self.title
