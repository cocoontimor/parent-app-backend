from rest_framework import viewsets

from utils.permissions import IsStaffGroupOrReadOnly

from .models import Child, Circle
from .serializers import ChildSerializer, CircleSerializer


class ChildViewSet(viewsets.ModelViewSet):
    serializer_class = ChildSerializer
    permission_classes = [IsStaffGroupOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="staff").exists():
            return Child.objects.all()
        return Child.objects.filter(circles__type="family", circles__members=user).distinct()


class CircleViewSet(viewsets.ModelViewSet):
    serializer_class = CircleSerializer
    permission_classes = [IsStaffGroupOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.groups.filter(name="staff").exists():
            return Circle.objects.all()
        return Circle.objects.filter(members=user)
