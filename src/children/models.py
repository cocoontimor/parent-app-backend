from django.conf import settings
from django.db import models

from utils.models import BaseModel


class Child(BaseModel):
    name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "children"
        verbose_name_plural = "children"

    def __str__(self):
        return self.name


class Circle(BaseModel):
    class Type(models.TextChoices):
        FAMILY = "family", "Family"
        CLASSROOM = "classroom", "Classroom"

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=Type.choices)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="circles",
        blank=True,
    )
    children = models.ManyToManyField(
        Child,
        related_name="circles",
        blank=True,
    )

    class Meta:
        db_table = "circles"

    def __str__(self):
        return f"{self.name} ({self.type})"
