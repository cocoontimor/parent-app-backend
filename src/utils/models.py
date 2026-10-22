from django.db import models
from ulid import ULID


def generate_ulid():
    return str(ULID())


class BaseModel(models.Model):
    id = models.CharField(
        primary_key=True,
        max_length=26,
        default=generate_ulid,
        editable=False,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DeletedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().exclude(deleted=None)


class UndeletedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted=None)


class SoftDeleteModel(models.Model):
    """Soft-delete mixin: ``deleted`` is null while live, a timestamp once
    removed. The default manager hides deleted rows (so ``objects`` and reverse
    relations skip them); ``objects_del`` and ``objects_all`` reach them when
    needed."""

    deleted = models.DateTimeField("Deleted date", blank=True, null=True)

    objects = UndeletedManager()
    objects_del = DeletedManager()
    objects_all = models.Manager()

    class Meta:
        abstract = True
