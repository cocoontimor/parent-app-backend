from django.conf import settings
from django.db import models

from utils.models import BaseModel


class Child(BaseModel):
    name = models.CharField(max_length=255)
    date_of_birth = models.DateField(null=True, blank=True)
    graduated = models.BooleanField(default=False)

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
    graduated = models.BooleanField(default=False)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="Member",
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


class Member(BaseModel):
    """A user's membership in a circle, carrying their relationship to it
    (e.g. a parent in a family circle). Through model for Circle.members."""

    class Relationship(models.TextChoices):
        MOTHER = "mother", "Mother"
        FATHER = "father", "Father"
        GUARDIAN = "guardian", "Guardian"
        TEACHER = "teacher", "Teacher"
        OTHER = "other", "Other"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    circle = models.ForeignKey(
        Circle,
        on_delete=models.CASCADE,
        related_name="member_records",
    )
    relationship = models.CharField(
        max_length=20,
        choices=Relationship.choices,
        blank=True,
    )

    class Meta:
        db_table = "members"
        unique_together = [("user", "circle")]

    def __str__(self):
        return f"{self.user} in {self.circle} ({self.relationship or 'member'})"
