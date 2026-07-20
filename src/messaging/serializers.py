from rest_framework import serializers

from .models import MessageLog


class MessageLogSerializer(serializers.ModelSerializer):
    recipient = serializers.CharField(source="recipient.display_name", read_only=True)

    class Meta:
        model = MessageLog
        fields = ["id", "recipient", "template", "body", "status", "sent_at", "created"]
        read_only_fields = fields
