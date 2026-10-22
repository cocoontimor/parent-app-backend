from rest_framework import serializers

from photos.serializers import PhotoSerializer

from .models import Update, UrgentAlert


class UpdateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    child_name = serializers.CharField(source="child.name", read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Update
        fields = [
            "id", "child", "child_name", "text", "photos",
            "created_by", "created_by_name", "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]


class UrgentAlertSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    # Populated by annotations in the index view (counts over MessageLog.source).
    recipient_count = serializers.IntegerField(read_only=True, default=0)
    ack_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = UrgentAlert
        fields = [
            "id", "title", "body", "created_by", "created_by_name",
            "recipient_count", "ack_count", "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]
