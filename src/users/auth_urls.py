from django.urls import path
from rest_framework.authtoken.views import obtain_auth_token

from .views import UserViewSet

urlpatterns = [
    path("login/", obtain_auth_token, name="auth-login"),
    path("me/", UserViewSet.as_view({"get": "me"}), name="auth-me"),
]
