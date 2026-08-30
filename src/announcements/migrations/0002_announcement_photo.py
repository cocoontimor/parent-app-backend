# Generated for adding multiple photos to Announcement

import django.db.models.deletion
import utils.models
from django.db import migrations, models


def announcement_photo_upload_path(instance, filename):
    # Kept locally so this historical migration stays importable after the
    # AnnouncementPhoto model was removed in favour of the generic Photo model.
    return f"announcements/{instance.announcement_id}/photos/{filename}"


class Migration(migrations.Migration):

    dependencies = [
        ('announcements', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AnnouncementPhoto',
            fields=[
                ('id', models.CharField(default=utils.models.generate_ulid, editable=False, max_length=26, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('image', models.ImageField(upload_to=announcement_photo_upload_path)),
                ('announcement', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='announcements.announcement')),
            ],
            options={
                'db_table': 'announcement_photos',
                'ordering': ['created'],
            },
        ),
    ]
