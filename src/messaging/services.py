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


ACK_PAYLOAD_PREFIX = "ACK:"


def send_text_message(recipient_phone, text):
    """Send a free-form text message via the Cloud API.

    Unlike ``send_whatsapp_message`` (which sends approved templates), a plain
    ``text`` message is only deliverable inside the 24-hour customer-service
    window — i.e. as a reply after the parent has messaged us. We use it for the
    magic-link reply. Returns True on success, False otherwise.
    """
    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    access_token = settings.WHATSAPP_ACCESS_TOKEN

    if not phone_number_id or not access_token:
        logger.warning(
            "WhatsApp credentials not configured, not sending text | to=%s",
            recipient_phone,
        )
        return False

    url = WHATSAPP_API_URL.format(phone_id=phone_number_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "text",
        "text": {"body": text},
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.ok:
            logger.info("WhatsApp text sent to %s", recipient_phone)
            return True
        logger.error(
            "WhatsApp text API error %s for %s: %s",
            resp.status_code,
            recipient_phone,
            resp.text[:200],
        )
    except requests.RequestException:
        logger.exception("WhatsApp text request failed for %s", recipient_phone)
    return False


def send_whatsapp_message(
    recipient_user, template, body, variables=None, button_payload=None,
    acknowledge=False, source=None,
):
    """
    Send a WhatsApp template message via the Cloud API.

    ``variables`` are the ordered values for the template's body placeholders
    ({{1}}, {{2}}, ...). The approved template must declare a matching number of
    body variables; the digest/alert templates use a single {{1}} that receives
    the composed ``body``.

    ``button_payload`` sets the developer-defined payload on the template's
    first quick-reply button. When the recipient taps it, WhatsApp posts an
    inbound ``button`` message carrying this payload back to our webhook.

    ``acknowledge=True`` makes this an acknowledgeable notification: the
    template's quick-reply button is given an ``ACK:<log id>`` payload, so the
    tap is attributed back to this exact MessageLog (see ``record_acknowledgment``).
    Ignored when an explicit ``button_payload`` is supplied.

    ``source`` optionally links the log to the object this message was sent for
    (e.g. an UrgentAlert), so acknowledgments can be reported per source.

    Falls back to logging if credentials are not configured.
    """
    from .models import MessageLog

    phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
    access_token = settings.WHATSAPP_ACCESS_TOKEN
    recipient_phone = recipient_user.username  # username stores E.164 phone

    # Create the log up front so an acknowledge button can reference its id.
    log = MessageLog.objects.create(
        recipient=recipient_user,
        template=template,
        body=body,
        status=MessageLog.Status.PENDING,
        source=source,
    )

    if not phone_number_id or not access_token:
        logger.warning(
            "WhatsApp credentials not configured, logging instead | to=%s",
            recipient_phone,
        )
        log.status = MessageLog.Status.FAILED
        log.error = "WhatsApp credentials not configured"
        log.save(update_fields=["status", "error", "modified"])
        return log

    if acknowledge and not button_payload:
        button_payload = f"{ACK_PAYLOAD_PREFIX}{log.id}"

    url = WHATSAPP_API_URL.format(phone_id=phone_number_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    template_payload = {
        "name": template,
        "language": {"code": "en"},
    }
    components = []
    if variables:
        components.append(
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": _sanitize_param(v)} for v in variables
                ],
            }
        )
    if button_payload:
        components.append(
            {
                "type": "button",
                "sub_type": "quick_reply",
                "index": 0,
                "parameters": [{"type": "payload", "payload": button_payload}],
            }
        )
    if components:
        template_payload["components"] = components
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient_phone,
        "type": "template",
        "template": template_payload,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.ok:
            log.status = MessageLog.Status.SENT
            log.sent_at = timezone.now()
            try:
                log.wa_message_id = resp.json()["messages"][0]["id"]
            except (ValueError, KeyError, IndexError):
                pass
            logger.info("WhatsApp sent to %s (template=%s)", recipient_phone, template)
        else:
            log.status = MessageLog.Status.FAILED
            log.error = resp.text[:500]
            logger.error(
                "WhatsApp API error %s for %s: %s",
                resp.status_code,
                recipient_phone,
                resp.text[:200],
            )
    except requests.RequestException as exc:
        log.status = MessageLog.Status.FAILED
        log.error = str(exc)[:500]
        logger.exception("WhatsApp request failed for %s", recipient_phone)

    log.save()
    return log


def record_acknowledgment(from_phone, payload):
    """Record an acknowledge button tap from the WhatsApp webhook.

    ``payload`` looks like ``ACK:<message log id>``. The log must belong to the
    sender so one parent can't acknowledge another's message. Returns the
    MessageLog, or None if the payload doesn't match or can't be attributed.
    """
    from .models import MessageLog

    if not payload or not payload.startswith(ACK_PAYLOAD_PREFIX):
        return None

    log_id = payload[len(ACK_PAYLOAD_PREFIX):].strip()
    log = MessageLog.objects.filter(id=log_id, recipient__username=from_phone).first()
    if log is None:
        logger.warning("Ack for unknown/mismatched message %s from %s", log_id, from_phone)
        return None

    if log.acknowledged_at is None:
        log.acknowledged_at = timezone.now()
        log.save(update_fields=["acknowledged_at", "modified"])
    logger.info("Message %s acknowledged by %s", log_id, from_phone)
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
