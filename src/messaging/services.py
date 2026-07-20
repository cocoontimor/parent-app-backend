import logging
import re

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

WHATSAPP_API_URL = "https://graph.facebook.com/v21.0/{phone_id}/messages"


def _sanitize_param(text):
    """WhatsApp body parameters cannot contain newlines, tabs, or runs of >4
    spaces. Collapse all whitespace to single spaces so content is accepted."""
    return re.sub(r"\s+", " ", str(text)).strip()


def send_whatsapp_message(recipient_user, template, body, variables=None):
    """
    Send a WhatsApp template message via the Cloud API.

    ``variables`` are the ordered values for the template's body placeholders
    ({{1}}, {{2}}, ...). The approved template must declare a matching number of
    body variables; the digest/alert templates use a single {{1}} that receives
    the composed ``body``.
    Falls back to logging if credentials are not configured.
    """
    from .models import MessageLog

    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    access_token = settings.WHATSAPP_ACCESS_TOKEN
    recipient_phone = recipient_user.username  # username stores E.164 phone

    if not phone_number_id or not access_token:
        logger.warning(
            "WhatsApp credentials not configured, logging instead | to=%s",
            recipient_phone,
        )
        return MessageLog.objects.create(
            recipient=recipient_user,
            template=template,
            body=body,
            status=MessageLog.Status.FAILED,
            error="WhatsApp credentials not configured",
        )

    url = WHATSAPP_API_URL.format(phone_id=phone_number_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    template_payload = {
        "name": template,
        "language": {"code": "en"},
    }
    if variables:
        template_payload["components"] = [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": _sanitize_param(v)} for v in variables
                ],
            }
        ]
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "template",
        "template": template_payload,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.ok:
            log = MessageLog.objects.create(
                recipient=recipient_user,
                template=template,
                body=body,
                status=MessageLog.Status.SENT,
                sent_at=timezone.now(),
            )
            logger.info("WhatsApp sent to %s (template=%s)", recipient_phone, template)
        else:
            log = MessageLog.objects.create(
                recipient=recipient_user,
                template=template,
                body=body,
                status=MessageLog.Status.FAILED,
                error=resp.text[:500],
            )
            logger.error(
                "WhatsApp API error %s for %s: %s",
                resp.status_code,
                recipient_phone,
                resp.text[:200],
            )
    except requests.RequestException as exc:
        log = MessageLog.objects.create(
            recipient=recipient_user,
            template=template,
            body=body,
            status=MessageLog.Status.FAILED,
            error=str(exc)[:500],
        )
        logger.exception("WhatsApp request failed for %s", recipient_phone)

    return log


def queue_announcement_for_digest(announcement):
    """Queue digest items for all recipient parents of an announcement."""
    from .models import DigestQueue

    parents = announcement.get_recipient_parents()
    items = [
        DigestQueue(
            recipient=parent,
            item_type=DigestQueue.ItemType.ANNOUNCEMENT,
            item_id=announcement.id,
        )
        for parent in parents
    ]
    DigestQueue.objects.bulk_create(items)
    logger.info("Queued announcement %s for %d parents", announcement.id, len(items))


def queue_update_for_digest(update):
    """Queue digest items for all parents of the child (via family circles)."""
    from django.contrib.auth import get_user_model
    from .models import DigestQueue

    User = get_user_model()
    parents = User.objects.filter(
        circles__type="family",
        circles__children=update.child,
    ).distinct()

    items = [
        DigestQueue(
            recipient=parent,
            item_type=DigestQueue.ItemType.UPDATE,
            item_id=update.id,
        )
        for parent in parents
    ]
    DigestQueue.objects.bulk_create(items)
    logger.info("Queued update %s for %d parents", update.id, len(items))
