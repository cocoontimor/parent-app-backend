from rest_framework import serializers

from photos.serializers import PhotoSerializer

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    photos = PhotoSerializer(many=True, read_only=True)
    recipient_count = serializers.SerializerMethodField()
    ack_count = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            "id", "title", "body", "created_by", "created_by_name",
            "circles", "photos", "recipient_count", "ack_count",
            "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]

    def _digest_items(self, obj):
        # Acks are attributed via the digest that delivered the announcement:
        # the DigestQueue row links a parent to the MessageLog they can ack.
        from messaging.models import DigestQueue

        return DigestQueue.objects.filter(
            item_type=DigestQueue.ItemType.ANNOUNCEMENT, item_id=obj.id
        )

    def get_recipient_count(self, obj):
        return self._digest_items(obj).values("recipient").distinct().count()

    def get_ack_count(self, obj):
        return (
            self._digest_items(obj)
            .filter(message_log__acknowledged_at__isnull=False)
            .values("recipient")
            .distinct()
            .count()
        )

    def _save_photos(self, announcement):
        request = self.context.get("request")
        if request is None:
            return
        from photos.models import Photo

        for image in request.FILES.getlist("photos"):
            Photo.objects.create(owner=announcement, image=image)

    def create(self, validated_data):
        announcement = super().create(validated_data)
        self._save_photos(announcement)
        return announcement

    def update(self, instance, validated_data):
        announcement = super().update(instance, validated_data)
        self._save_photos(announcement)
        return announcement
