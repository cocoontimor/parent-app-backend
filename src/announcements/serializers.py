from rest_framework import serializers

from .models import Announcement, AnnouncementAck, AnnouncementPhoto


class AnnouncementPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnouncementPhoto
        fields = ["id", "image", "created"]
        read_only_fields = ["id", "created"]


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    ack_count = serializers.SerializerMethodField()
    photos = AnnouncementPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = Announcement
        fields = [
            "id", "title", "body", "created_by", "created_by_name",
            "circles", "photos", "ack_count", "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]

    def get_ack_count(self, obj):
        return obj.acks.count()

    def _save_photos(self, announcement):
        request = self.context.get("request")
        if request is None:
            return
        for image in request.FILES.getlist("photos"):
            AnnouncementPhoto.objects.create(announcement=announcement, image=image)

    def create(self, validated_data):
        announcement = super().create(validated_data)
        self._save_photos(announcement)
        return announcement

    def update(self, instance, validated_data):
        announcement = super().update(instance, validated_data)
        self._save_photos(announcement)
        return announcement


class AnnouncementAckSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.display_name", read_only=True)

    class Meta:
        model = AnnouncementAck
        fields = ["id", "parent", "parent_name", "created"]
        read_only_fields = ["id", "parent", "created"]
