from django.contrib.auth.models import AbstractUser
from django.db import models

from utils.models import generate_ulid

class User(AbstractUser):
    id = models.CharField(
        primary_key=True,
        max_length=26,
        default=generate_ulid,
        editable=False,
    )
    email = models.EmailField(blank=True)
    username = models.CharField(max_length=150, unique=True)
    full_name = models.CharField(max_length=255, blank=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"

    @property
    def display_name(self):
        return self.full_name or self.username
