from rest_framework import serializers

from .models import Announcement, AnnouncementAck


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    ack_count = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id", "title", "body", "created_by", "created_by_name",
            "circles", "ack_count", "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]

    def get_ack_count(self, obj):
        return obj.acks.count()


class AnnouncementAckSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.display_name", read_only=True)

    class Meta:
        model = AnnouncementAck
        fields = ["id", "parent", "parent_name", "created"]
        read_only_fields = ["id", "parent", "created"]
