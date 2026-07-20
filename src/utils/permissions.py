from rest_framework.permissions import IsAuthenticated


class IsStaffGroupOrReadOnly(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.groups.filter(name="staff").exists()
