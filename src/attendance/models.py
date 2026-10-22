from django.conf import settings
from django.db import models

from utils.models import BaseModel


class Attendance(BaseModel):
    """A child's attendance for a classroom on a given day, marked by staff.

    One record per (child, circle, date); re-marking updates it in place.
    """

    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"

    child = models.ForeignKey(
        "children.Child",
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    circle = models.ForeignKey(
        "children.Circle",
        on_delete=models.CASCADE,
        related_name="attendances",
    )
    date = models.DateField()
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PRESENT,
    )
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_attendances",
    )

    class Meta:
        db_table = "attendance"
        ordering = ["-date"]
        unique_together = [("child", "circle", "date")]

    def __str__(self):
        return f"{self.child} — {self.date}: {self.status}"
