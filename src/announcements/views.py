from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from utils.permissions import IsStaffGroupOrReadOnly
from .models import Announcement, AnnouncementAck
from .serializers import AnnouncementSerializer, AnnouncementAckSerializer


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    permission_classes = [IsStaffGroupOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="staff").exists():
            return Announcement.objects.all()
        # Parents see announcements with no circles (all) or where they're in a target circle
        return Announcement.objects.filter(
            circles__isnull=True
        ).union(
            Announcement.objects.filter(circles__members=user)
        )

    def perform_create(self, serializer):
        announcement = serializer.save(created_by=self.request.user)
        from messaging.services import queue_announcement_for_digest
        queue_announcement_for_digest(announcement)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def acknowledge(self, request, pk=None):
        announcement = self.get_object()
        _, created = AnnouncementAck.objects.get_or_create(
            announcement=announcement,
            parent=request.user,
        )
        if created:
            return Response({"status": "acknowledged"}, status=status.HTTP_201_CREATED)
        return Response({"status": "already acknowledged"})

    @action(detail=True, methods=["get"])
    def acks(self, request, pk=None):
        announcement = self.get_object()
        acks = announcement.acks.select_related("parent").all()
        serializer = AnnouncementAckSerializer(acks, many=True)
        return Response(serializer.data)
