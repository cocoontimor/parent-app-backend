from django.db import migrations

# Timezone the schedules run in. Editable per-schedule in the Django admin.
SCHEDULE_TZ = "Asia/Dili"  # Timor-Leste (UTC+9)

TASKS = [
    {"name": "send-daily-digest", "task": "messaging.tasks.send_daily_digest", "hour": 15, "minute": 0},
    {"name": "release-due-lessons", "task": "elearning.tasks.release_due_lessons", "hour": 14, "minute": 0},
]


def seed(apps, schema_editor):
    CrontabSchedule = apps.get_model("django_celery_beat", "CrontabSchedule")
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    for t in TASKS:
        cron, _ = CrontabSchedule.objects.get_or_create(
            minute=str(t["minute"]),
            hour=str(t["hour"]),
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone=SCHEDULE_TZ,
        )
        PeriodicTask.objects.get_or_create(
            name=t["name"],
            defaults={"task": t["task"], "crontab": cron},
        )


def unseed(apps, schema_editor):
    PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
    PeriodicTask.objects.filter(name__in=[t["name"] for t in TASKS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0003_messagelog_acknowledged_at_messagelog_wa_message_id_and_more"),
        ("django_celery_beat", "0019_alter_periodictasks_options"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
