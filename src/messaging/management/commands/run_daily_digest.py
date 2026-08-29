"""Send the daily WhatsApp digest.

Invoked by a Cloud Run Job on a Cloud Scheduler cron (replaces Celery beat).
"""
from django.core.management.base import BaseCommand

from messaging.tasks import send_daily_digest


class Command(BaseCommand):
    help = "Send the daily digest to parents with pending items."

    def handle(self, *args, **options):
        send_daily_digest()
        self.stdout.write(self.style.SUCCESS("Daily digest run complete."))
