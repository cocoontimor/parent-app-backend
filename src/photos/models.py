from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from utils.models import BaseModel


def photo_upload_path(instance, filename):
    return f"photos/{instance.owner_type.model}/{instance.owner_id}/{filename}"


class Photo(BaseModel):
    """An image attached to any owner object (Announcement, Update, ...) via a
    generic FK, so photo handling is shared instead of duplicated per model.
    owner_id is a CharField to match the app's ULID primary keys."""

    owner_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    owner_id = models.CharField(max_length=26, db_index=True)
    owner = GenericForeignKey("owner_type", "owner_id")
    image = models.ImageField(upload_to=photo_upload_path)

    class Meta:
        db_table = "photos"
        ordering = ["created"]

    def __str__(self):
        return f"Photo for {self.owner_type}:{self.owner_id}"
