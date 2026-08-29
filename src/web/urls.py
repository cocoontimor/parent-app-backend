from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    # Public, self-contained privacy policy (no login, not Inertia).
    path(
        "privacy/",
        TemplateView.as_view(template_name="privacy.html"),
        name="privacy",
    ),
    # Auth
    path("login/", views.login_page, name="login"),
    path("login/submit/", views.login_submit, name="login_submit"),
    path("logout/", views.logout_submit, name="logout"),
    # Passwordless login from a WhatsApp magic link
    path("m/<str:token>/", views.magic_login, name="magic_login"),
    # Children (updates live on the child detail page)
    path("children/", views.children_index, name="children"),
    path("children/create/", views.children_create, name="children_create"),
    path("children/<str:pk>/graduate/", views.children_graduate, name="children_graduate"),
    path("children/<str:pk>/", views.children_show, name="children_show"),
    path("updates/create/", views.updates_create, name="updates_create"),
    # Classes (Circle model/logic, exposed under /classes/)
    path("classes/", views.classes_index, name="classes"),
    path("classes/create/", views.classes_create, name="classes_create"),
    path("classes/<str:pk>/graduate/", views.classes_graduate, name="classes_graduate"),
    # Users
    path("users/", views.users_index, name="users"),
    # Announcements
    path("announcements/", views.announcements_index, name="announcements"),
    path("announcements/create/", views.announcements_create, name="announcements_create"),
    path("announcements/<str:pk>/", views.announcements_show, name="announcements_show"),
    # Urgent alerts
    path("urgent-alerts/", views.urgent_alerts_index, name="urgent_alerts"),
    path("urgent-alerts/create/", views.urgent_alerts_create, name="urgent_alerts_create"),
    # Payments (school fees)
    path("payments/", views.payments_index, name="payments"),
    path("payments/create/", views.payments_create, name="payments_create"),
    path(
        "payments/<str:pk>/send-confirmation/",
        views.payments_send_confirmation,
        name="payments_send_confirmation",
    ),
    # Messages
    path("messages/", views.messages_index, name="messages"),
    # E-Learning
    path("elearning/", views.elearning_index, name="elearning"),
    path("elearning/courses/create/", views.courses_create, name="courses_create"),
    path("elearning/courses/<str:pk>/", views.courses_show, name="courses_show"),
    path("elearning/modules/create/", views.modules_create, name="modules_create"),
    path("elearning/lessons/create/", views.lessons_create, name="lessons_create"),
    path("elearning/cohorts/create/", views.cohorts_create, name="cohorts_create"),
    path("elearning/cohorts/<str:pk>/", views.cohorts_show, name="cohorts_show"),
]
