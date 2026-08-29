import hashlib
import hmac
import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import InboundMessage, MessageLog

logger = logging.getLogger(__name__)

# Texting any of these opens the view-only app via a magic link.
APP_LINK_KEYWORDS = {"menu", "app", "hi", "hello", "start"}


def _maybe_send_app_link(from_phone, text):
    """If a known parent texts a keyword, reply with a magic link to the app.

    Runs inside the 24h customer-service window (the parent just messaged us), so
    a free-form text reply is allowed without a template.
    """
    from django.contrib.auth import get_user_model
    from django.urls import reverse

    if (text or "").strip().lower() not in APP_LINK_KEYWORDS:
        return

    user = get_user_model().objects.filter(username=from_phone).first()
    if user is None:
        return

    from web.tokens import make_login_token

    from .services import send_text_message

    link = settings.APP_BASE_URL.rstrip("/") + reverse(
        "magic_login", args=[make_login_token(user)]
    )
    send_text_message(
        from_phone,
        f"Tap to open Cocoon and view your updates (link valid ~15 min): {link}",
    )


def _valid_signature(request):
    """Verify Meta's X-Hub-Signature-256 header against the app secret.

    Returns True only when the signature matches. When no app secret is
    configured we fail closed (reject) so unverified webhooks are never
    processed in production; the sole exception is local development
    (settings.DEBUG), where a missing secret is allowed.
    """
    secret = settings.WHATSAPP_APP_SECRET
    if not secret:
        if settings.DEBUG:
            return True
        logger.error(
            "WHATSAPP_APP_SECRET is not set; rejecting unverified webhook"
        )
        return False

    header = request.headers.get("X-Hub-Signature-256", "")
    if not header.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode(), request.body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(header[len("sha256="):], expected)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def whatsapp_webhook(request):
    """
    WhatsApp Cloud API webhook.
    GET  - verification challenge from Meta.
    POST - delivery status updates and inbound messages.
    """
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode == "subscribe" and token == settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN:
            return HttpResponse(challenge, content_type="text/plain")
        return HttpResponse("Forbidden", status=403)

    # POST — process incoming webhook events
    if not _valid_signature(request):
        logger.warning("Rejected WhatsApp webhook with invalid signature")
        return HttpResponse("Forbidden", status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid json"}, status=400)

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Delivery status updates
            for status in value.get("statuses", []):
                _handle_status_update(status)

            # Inbound messages
            for message in value.get("messages", []):
                _handle_inbound_message(message, value.get("metadata", {}))

    return JsonResponse({"status": "ok"})


def _handle_status_update(status):
    """Update MessageLog when we get a delivery/read receipt.

    Receipts carry WhatsApp's message id, so we target the exact MessageLog
    rather than every message to the same phone. Statuses only ever advance
    (sent → delivered → read), so we never downgrade an already-read message.
    """
    wa_status = status.get("status")  # sent, delivered, read, failed
    wa_message_id = status.get("id")
    recipient_phone = status.get("recipient_id")

    if not wa_message_id:
        return

    logs = MessageLog.objects.filter(wa_message_id=wa_message_id)

    if wa_status == "delivered":
        logs.filter(status=MessageLog.Status.SENT).update(
            status=MessageLog.Status.DELIVERED
        )
        logger.info("Delivery confirmed for %s", recipient_phone)
    elif wa_status == "read":
        logs.filter(
            status__in=[MessageLog.Status.SENT, MessageLog.Status.DELIVERED]
        ).update(status=MessageLog.Status.READ)
        logger.info("Read confirmed for %s", recipient_phone)
    elif wa_status == "failed":
        errors = status.get("errors", [{}])
        error_msg = errors[0].get("title", "Unknown error") if errors else "Unknown error"
        logs.update(status=MessageLog.Status.FAILED, error=error_msg)
        logger.warning("Delivery failed for %s: %s", recipient_phone, error_msg)


def _handle_inbound_message(message, metadata):
    """Persist inbound messages from parents. Template quick-reply buttons
    arrive as type ``button`` carrying the payload we set when sending."""
    from django.contrib.auth import get_user_model

    from_phone = message.get("from")
    msg_type = message.get("type")
    wa_message_id = message.get("id")

    if msg_type == "button":
        payload = message.get("button", {}).get("payload", "")
        from elearning.services import record_completion

        from .services import record_acknowledgment

        # Each recogniser no-ops on a payload prefix it doesn't own.
        if record_completion(from_phone, payload):
            logger.info("Recorded lesson completion from %s", from_phone)
        elif record_acknowledgment(from_phone, payload):
            logger.info("Recorded acknowledgment from %s", from_phone)

    text = message.get("text", {}).get("body", "") if msg_type == "text" else ""

    if msg_type == "text" and from_phone:
        _maybe_send_app_link(from_phone, text)

    if not wa_message_id:
        logger.info("Inbound WhatsApp from %s with no message id, skipping store", from_phone)
        return

    User = get_user_model()
    sender = User.objects.filter(username=from_phone).first()

    # get_or_create keyed on the WhatsApp message id makes redelivered
    # webhooks idempotent.
    InboundMessage.objects.get_or_create(
        wa_message_id=wa_message_id,
        defaults={
            "sender": sender,
            "from_phone": from_phone or "",
            "message_type": msg_type or "",
            "text": text,
            "payload": message,
        },
    )
    logger.info("Stored inbound WhatsApp from %s: %s", from_phone, text[:100])
