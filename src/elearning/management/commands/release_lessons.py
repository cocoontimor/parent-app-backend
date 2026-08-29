"""Release any e-learning lessons that have come due.

Invoked hourly by a Cloud Run Job on a Cloud Scheduler cron (replaces Celery
beat). The per-cohort ``send_hour`` gating lives in ``release_due_lessons``.
"""
from django.core.management.base import BaseCommand

from elearning.tasks import release_due_lessons


class Command(BaseCommand):
    help = "Release due e-learning lessons for cohorts whose send_hour matches now."

    def handle(self, *args, **options):
        released = release_due_lessons()
        self.stdout.write(self.style.SUCCESS(f"Released {released} lesson(s)."))
