from django.urls import include, path
from rest_framework.routers import DefaultRouter

from announcements.views import AnnouncementViewSet
from children.views import ChildViewSet, CircleViewSet
from messaging.views import MessageLogViewSet
from updates.views import UpdateViewSet, UrgentAlertViewSet
from users.views import UserViewSet

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(r"children", ChildViewSet, basename="children")
router.register(r"circles", CircleViewSet, basename="circles")
router.register(r"announcements", AnnouncementViewSet, basename="announcements")
router.register(r"updates", UpdateViewSet, basename="updates")
router.register(r"urgent-alerts", UrgentAlertViewSet, basename="urgent-alerts")
router.register(r"messages", MessageLogViewSet, basename="messages")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("users.auth_urls")),
]
