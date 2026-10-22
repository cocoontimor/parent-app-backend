from django.db import migrations


def create_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="trainee")


def remove_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="trainee").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0002_create_groups"),
    ]

    operations = [
        migrations.RunPython(create_group, remove_group),
    ]
