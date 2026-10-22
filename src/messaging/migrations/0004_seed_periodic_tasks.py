from django.db import migrations

# Historically this migration seeded django-celery-beat PeriodicTask rows for the
# daily digest and hourly lesson release. Those jobs now run as Cloud Run Jobs on
# Cloud Scheduler crons (see the `run_daily_digest` and `release_lessons`
# management commands), and django-celery-beat has been removed. The migration is
# retained as a no-op so the recorded history stays intact for later migrations.


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0003_messagelog_acknowledged_at_messagelog_wa_message_id_and_more"),
    ]

    operations = []
