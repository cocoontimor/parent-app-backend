from django.db import migrations


def mark_existing_paid(apps, schema_editor):
    """Existing rows were logged payments, so treat them as already paid
    (stamp paid_at from when they were recorded)."""
    FeePayment = apps.get_model("payments", "FeePayment")
    for p in FeePayment.objects.all():
        p.status = "paid"
        p.paid_at = p.created
        p.save(update_fields=["status", "paid_at"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("payments", "0002_feepayment_marked_by_feepayment_paid_at_and_more"),
    ]

    operations = [migrations.RunPython(mark_existing_paid, noop)]
