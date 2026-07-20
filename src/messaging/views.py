import json
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, mixins

from utils.permissions import IsStaffGroupOrReadOnly
from .models import MessageLog
from .serializers import MessageLogSerializer

logger = logging.getLogger(__name__)


class MessageLogViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = MessageLogSerializer
    permission_classes = [IsStaffGroupOrReadOnly]
    queryset = MessageLog.objects.select_related("recipient").all()


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
    """Update MessageLog when we get a delivery receipt."""
    wa_status = status.get("status")  # sent, delivered, read, failed
    recipient_phone = status.get("recipient_id")

    if wa_status == "delivered":
        MessageLog.objects.filter(
            recipient__username=recipient_phone,
            status=MessageLog.Status.SENT,
        ).update(status=MessageLog.Status.DELIVERED)
        logger.info("Delivery confirmed for %s", recipient_phone)
    elif wa_status == "failed":
        errors = status.get("errors", [{}])
        error_msg = errors[0].get("title", "Unknown error") if errors else "Unknown error"
        MessageLog.objects.filter(
            recipient__username=recipient_phone,
            status=MessageLog.Status.SENT,
        ).update(status=MessageLog.Status.FAILED, error=error_msg)
        logger.warning("Delivery failed for %s: %s", recipient_phone, error_msg)


def _handle_inbound_message(message, metadata):
    """Log inbound messages from parents. Extend this for replies."""
    from_phone = message.get("from")
    msg_type = message.get("type")
    text = message.get("text", {}).get("body", "") if msg_type == "text" else f"[{msg_type}]"
    logger.info("Inbound WhatsApp from %s: %s", from_phone, text[:100])
