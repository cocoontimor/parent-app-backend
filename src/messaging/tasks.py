import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_daily_digest():
    """
    Daily digest job. For each parent with pending digest items,
    compose one message and send via WhatsApp stub.
    """
    from django.contrib.auth import get_user_model

    from announcements.models import Announcement
    from updates.models import Update
    from .models import DigestQueue
    from .services import send_whatsapp_message

    User = get_user_model()

    pending = DigestQueue.objects.filter(processed=False).select_related("recipient")

    recipients = {}
    for item in pending:
        recipients.setdefault(item.recipient_id, []).append(item)

    for recipient_id, items in recipients.items():
        user = items[0].recipient
        lines = [f"You have {len(items)} new item(s):"]

        for item in items:
            if item.item_type == DigestQueue.ItemType.ANNOUNCEMENT:
                try:
                    ann = Announcement.objects.get(id=item.item_id)
                    lines.append(f"- Announcement: {ann.title}")
                except Announcement.DoesNotExist:
                    pass
            elif item.item_type == DigestQueue.ItemType.UPDATE:
                try:
                    upd = Update.objects.select_related("child").get(id=item.item_id)
                    lines.append(f"- Update for {upd.child.name}: {upd.text[:80]}")
                except Update.DoesNotExist:
                    pass

        body = "\n".join(lines)
        send_whatsapp_message(user, template="daily_digest", body=body, variables=[body])

        DigestQueue.objects.filter(
            id__in=[item.id for item in items]
        ).update(processed=True)

    logger.info("Daily digest sent to %d parents", len(recipients))


@shared_task
def send_urgent_alert(alert_id):
    """Immediate send for urgent alerts. Bypasses digest. Sends to ALL parents."""
    from django.contrib.auth import get_user_model

    from updates.models import UrgentAlert
    from .services import send_whatsapp_message

    User = get_user_model()

    try:
        alert = UrgentAlert.objects.get(id=alert_id)
    except UrgentAlert.DoesNotExist:
        logger.error("UrgentAlert %s not found", alert_id)
        return

    parents = User.objects.filter(groups__name="parent")
    body = f"URGENT: {alert.title}\n\n{alert.body}"

    for parent in parents:
        send_whatsapp_message(parent, template="urgent_alert", body=body, variables=[body])

    logger.info("Urgent alert %s sent to %d parents", alert_id, parents.count())
