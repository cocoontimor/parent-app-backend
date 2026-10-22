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
    path("children/<str:pk>/edit/", views.children_update, name="children_update"),
    path("children/<str:pk>/family/", views.children_family_update, name="children_family_update"),
    path("parents/search/", views.parents_search, name="parents_search"),
    path("children/<str:pk>/", views.children_show, name="children_show"),
    path("updates/create/", views.updates_create, name="updates_create"),
    # Classes (Circle model/logic, exposed under /classes/)
    path("classes/", views.classes_index, name="classes"),
    path("classes/create/", views.classes_create, name="classes_create"),
    path("classes/<str:pk>/edit/", views.classes_update, name="classes_update"),
    path("classes/<str:pk>/graduate/", views.classes_graduate, name="classes_graduate"),
    path("classes/<str:pk>/attendance/", views.classes_attendance, name="classes_attendance"),
    path(
        "classes/<str:pk>/attendance/save/",
        views.classes_attendance_save,
        name="classes_attendance_save",
    ),
    # Users
    path("users/", views.users_index, name="users"),
    path("users/create/", views.users_create, name="users_create"),
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
    path("payments/generate/", views.payments_generate, name="payments_generate"),
    path("payments/<str:pk>/mark/", views.payments_mark, name="payments_mark"),
    path(
        "payments/<str:pk>/send-confirmation/",
        views.payments_send_confirmation,
        name="payments_send_confirmation",
    ),
    # Messages
    path("messages/", views.messages_index, name="messages"),
    # E-Learning
    path("elearning/", views.elearning_index, name="elearning"),
    path("elearning/courses/", views.courses_index, name="courses"),
    path("elearning/courses/create/", views.courses_create, name="courses_create"),
    path("elearning/courses/<str:pk>/edit/", views.courses_update, name="courses_update"),
    path("elearning/courses/<str:pk>/", views.courses_show, name="courses_show"),
    path("elearning/modules/create/", views.modules_create, name="modules_create"),
    path("elearning/modules/<str:pk>/edit/", views.modules_update, name="modules_update"),
    path("elearning/modules/<str:pk>/reorder/", views.modules_reorder, name="modules_reorder"),
    path("elearning/modules/<str:pk>/delete/", views.modules_delete, name="modules_delete"),
    path("elearning/lessons/create/", views.lessons_create, name="lessons_create"),
    path("elearning/lessons/<str:pk>/edit/", views.lessons_update, name="lessons_update"),
    path("elearning/lessons/<str:pk>/reorder/", views.lessons_reorder, name="lessons_reorder"),
    path("elearning/lessons/<str:pk>/delete/", views.lessons_delete, name="lessons_delete"),
    path("elearning/cohorts/", views.cohorts_index, name="cohorts"),
    path("elearning/cohorts/create/", views.cohorts_create, name="cohorts_create"),
    path("elearning/cohorts/<str:pk>/runs/create/", views.runs_create, name="runs_create"),
    path("elearning/cohorts/<str:pk>/", views.cohorts_show, name="cohorts_show"),
]
