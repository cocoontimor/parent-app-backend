from rest_framework import viewsets

from utils.permissions import IsStaffGroupOrReadOnly

from .models import Update, UrgentAlert
from .serializers import UpdateSerializer, UrgentAlertSerializer


class UpdateViewSet(viewsets.ModelViewSet):
    serializer_class = UpdateSerializer
    permission_classes = [IsStaffGroupOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="staff").exists():
            return Update.objects.select_related("child", "created_by").all()
        return Update.objects.select_related("child", "created_by").filter(
            child__circles__type="family",
            child__circles__members=user,
        ).distinct()

    def perform_create(self, serializer):
        update = serializer.save(created_by=self.request.user)
        from messaging.services import queue_update_for_digest
        queue_update_for_digest(update)


class UrgentAlertViewSet(viewsets.ModelViewSet):
    serializer_class = UrgentAlertSerializer
    permission_classes = [IsStaffGroupOrReadOnly]
    queryset = UrgentAlert.objects.select_related("created_by").all()

    def perform_create(self, serializer):
        alert = serializer.save(created_by=self.request.user)
        from messaging.tasks import send_urgent_alert
        send_urgent_alert.delay(alert.id)
