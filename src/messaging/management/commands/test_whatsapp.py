import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Send a test WhatsApp message using the hello_world template"

    def add_arguments(self, parser):
        parser.add_argument("phone", help="Recipient phone in E.164 format, e.g. +67012345678")

    def handle(self, *args, **options):
        phone = options["phone"]
        phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        access_token = settings.WHATSAPP_ACCESS_TOKEN

        if not phone_number_id or not access_token:
            self.stderr.write("WHATSAPP_PHONE_NUMBER_ID and WHATSAPP_ACCESS_TOKEN must be set in .env")
            return

        url = f"https://graph.facebook.com/v21.0/{phone_number_id}/messages"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": "hello_world",
                "language": {"code": "en_US"},
            },
        }

        self.stdout.write(f"Sending hello_world template to {phone}...")
        resp = requests.post(url, json=payload, headers=headers, timeout=10)

        if resp.ok:
            data = resp.json()
            msg_id = data.get("messages", [{}])[0].get("id", "unknown")
            self.stdout.write(self.style.SUCCESS(f"Sent! Message ID: {msg_id}"))
        else:
            self.stderr.write(self.style.ERROR(f"Failed ({resp.status_code}): {resp.text}"))
