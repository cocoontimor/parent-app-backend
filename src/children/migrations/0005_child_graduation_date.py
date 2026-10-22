from django.db import migrations, models


def graduated_to_date(apps, schema_editor):
    """Carry the old boolean forward: graduated children get a graduation_date.
    The true date is unknown, so use the record's modified timestamp as a proxy."""
    Child = apps.get_model("children", "Child")
    for child in Child.objects.filter(graduated=True):
        Child.objects.filter(pk=child.pk).update(graduation_date=child.modified.date())


def date_to_graduated(apps, schema_editor):
    Child = apps.get_model("children", "Child")
    Child.objects.filter(graduation_date__isnull=False).update(graduated=True)


class Migration(migrations.Migration):

    dependencies = [
        ("children", "0004_child_graduated_circle_graduated"),
    ]

    operations = [
        migrations.AddField(
            model_name="child",
            name="graduation_date",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Date the child graduated. Null means still active.",
            ),
        ),
        migrations.RunPython(graduated_to_date, date_to_graduated),
        migrations.RemoveField(
            model_name="child",
            name="graduated",
        ),
    ]
