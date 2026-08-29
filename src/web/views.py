"""
Inertia (Svelte) views for the Cocoon admin. Replaces the standalone Next.js
`app-admin` frontend: pages are rendered server-side with props instead of the
client fetching a DRF API. Auth is session-based (django.contrib.auth); writes
are gated to the "staff" group, mirroring the old IsStaffGroupOrReadOnly.

Read props reuse the existing DRF serializers so the shape stays identical to
what the React pages consumed.
"""
import json
import re

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from inertia import inertia, render

from announcements.models import Announcement
from announcements.serializers import AnnouncementAckSerializer, AnnouncementSerializer
from children.models import Child, Circle, Member
from children.serializers import ChildSerializer, CircleSerializer
from elearning.models import Cohort, Course, Lesson, LessonCompletion, Module
from elearning.serializers import (
    CohortSerializer,
    CourseSerializer,
    LessonReleaseSerializer,
)
from messaging.models import MessageLog
from messaging.serializers import MessageLogSerializer
from updates.models import Update, UrgentAlert
from updates.serializers import UpdateSerializer, UrgentAlertSerializer
from users.models import User
from users.serializers import UserSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _is_staff(user):
    return user.groups.filter(name="staff").exists()


def _require_staff(request):
    if not _is_staff(request.user):
        raise PermissionDenied("Staff group required.")


def _deny_non_staff(request):
    """Redirect non-staff (parent) users away from staff-only read pages.

    Returns an HttpResponseRedirect to bounce on, or None when the user is staff
    and may proceed.
    """
    if not _is_staff(request.user):
        return HttpResponseRedirect("/")
    return None


def _data(request):
    """Inertia posts JSON when there are no files, form-encoded otherwise."""
    ctype = request.content_type or ""
    if "application/json" in ctype:
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def _list(data, key):
    if hasattr(data, "getlist"):
        return data.getlist(key)
    value = data.get(key)
    if isinstance(value, list):
        return value
    return [value] if value else []


def _children_qs(user):
    if _is_staff(user):
        return Child.objects.all()
    return Child.objects.filter(
        circles__type="family", circles__members=user
    ).distinct()


def _circles_qs(user):
    if _is_staff(user):
        return Circle.objects.all()
    return Circle.objects.filter(members=user)


def _announcements_qs(user):
    if _is_staff(user):
        return Announcement.objects.all()
    return Announcement.objects.filter(circles__isnull=True).union(
        Announcement.objects.filter(circles__members=user)
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def login_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect("/")
    return render(request, "Auth/Login", props={})


@require_POST
def login_submit(request):
    data = _data(request)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None:
        return render(
            request,
            "Auth/Login",
            props={"errors": {"username": "Invalid username or password."}},
        )
    login(request, user)
    return HttpResponseRedirect("/")


@require_POST
def logout_submit(request):
    logout(request)
    return HttpResponseRedirect("/login/")


# Parents stay logged in for a month so a magic link isn't a daily chore.
PARENT_SESSION_AGE = 60 * 60 * 24 * 30


def magic_login(request, token):
    """Log a parent in from a WhatsApp magic link, then land them on the app."""
    from .tokens import resolve_login_token

    user = resolve_login_token(token)
    if user is None:
        return render(
            request,
            "Auth/Login",
            props={"errors": {"username": "That link has expired. Message us again for a new one."}},
        )
    # Explicit backend: allauth adds a second auth backend, so login() can't
    # infer which one to attribute this session to.
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    if not _is_staff(user):
        request.session.set_expiry(PARENT_SESSION_AGE)
    return HttpResponseRedirect("/")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@login_required
@inertia("Dashboard")
def dashboard(request):
    announcements = _announcements_qs(request.user)
    children = _children_qs(request.user).filter(graduated=False)
    classes = _circles_qs(request.user).filter(
        type=Circle.Type.CLASSROOM, graduated=False
    )
    return {
        "children": ChildSerializer(children, many=True).data,
        "circles": CircleSerializer(classes, many=True).data,
        "announcements": AnnouncementSerializer(announcements, many=True).data,
    }


# ---------------------------------------------------------------------------
# Children
# ---------------------------------------------------------------------------
@login_required
@inertia("Children")
def children_index(request):
    graduated = request.GET.get("graduated") == "1"
    children = _children_qs(request.user).filter(graduated=graduated)
    return {
        "children": ChildSerializer(children, many=True).data,
        "graduated": graduated,
    }


@require_POST
@login_required
def children_graduate(request, pk):
    _require_staff(request)
    child = get_object_or_404(Child, pk=pk)
    child.graduated = not child.graduated
    child.save(update_fields=["graduated"])
    # Stay on whichever view (current/graduated) the action came from.
    dest = "/children/?graduated=1" if _data(request).get("graduated") else "/children/"
    return HttpResponseRedirect(dest)


@require_POST
@login_required
@transaction.atomic
def children_create(request):
    _require_staff(request)
    data = _data(request)
    name = (data.get("name") or "").strip()

    child = Child.objects.create(
        name=name,
        date_of_birth=data.get("date_of_birth") or None,
    )

    # Every child gets a family circle grouping it with its parents.
    circle = Circle.objects.create(
        name=f"{name} Family" if name else "Family",
        type=Circle.Type.FAMILY,
    )
    circle.children.add(child)

    parent_group, _ = Group.objects.get_or_create(name="parent")
    for row in _list(data, "parents")[:4]:
        # Store digits only so it matches what WhatsApp posts back on its
        # webhook (bare E.164, no "+"/spaces/punctuation).
        number = re.sub(r"\D", "", row.get("number") or "")
        if not number:
            continue
        full_name = (row.get("full_name") or "").strip()
        relationship = row.get("relationship") or ""
        parent, created = User.objects.get_or_create(
            username=number,
            defaults={"full_name": full_name},
        )
        if not created and full_name and parent.full_name != full_name:
            parent.full_name = full_name
            parent.save(update_fields=["full_name"])
        parent.groups.add(parent_group)
        # Membership carries the relationship to this family circle.
        Member.objects.update_or_create(
            circle=circle,
            user=parent,
            defaults={"relationship": relationship},
        )

    return HttpResponseRedirect("/children/")


@login_required
@inertia("Children/Show")
def children_show(request, pk):
    child = get_object_or_404(_children_qs(request.user), pk=pk)
    classes = [
        {
            "id": circle.id,
            "name": circle.name,
            "type": circle.type,
            "parents": [
                {
                    "id": mr.user.pk,
                    "name": mr.user.display_name,
                    "relationship": mr.relationship,
                }
                for mr in circle.member_records.all()
            ],
        }
        for circle in child.circles.prefetch_related("member_records__user").all()
    ]
    updates = (
        Update.objects.select_related("created_by")
        .filter(child=child)
        .order_by("-created")
    )
    return {
        "child": ChildSerializer(child).data,
        "classes": classes,
        "updates": UpdateSerializer(updates, many=True).data,
    }


# ---------------------------------------------------------------------------
# Classes (Circle model/logic, exposed under /classes/)
# ---------------------------------------------------------------------------
@login_required
@inertia("Classes")
def classes_index(request):
    graduated = request.GET.get("graduated") == "1"
    classes = _circles_qs(request.user).filter(
        type=Circle.Type.CLASSROOM, graduated=graduated
    )
    users = User.objects.all() if _is_staff(request.user) else User.objects.filter(pk=request.user.pk)
    return {
        "circles": CircleSerializer(classes, many=True).data,
        "children": ChildSerializer(
            _children_qs(request.user).filter(graduated=False), many=True
        ).data,
        "users": UserSerializer(users, many=True).data,
        "graduated": graduated,
    }


@require_POST
@login_required
def classes_create(request):
    _require_staff(request)
    data = _data(request)
    circle = Circle.objects.create(
        name=data.get("name", ""),
        type=Circle.Type.CLASSROOM,
    )
    # Members selected for a class are its teachers.
    for user_id in _list(data, "members"):
        Member.objects.update_or_create(
            circle=circle,
            user_id=user_id,
            defaults={"relationship": Member.Relationship.TEACHER},
        )
    circle.children.set(_list(data, "children"))
    return HttpResponseRedirect("/classes/")


@require_POST
@login_required
def classes_graduate(request, pk):
    _require_staff(request)
    circle = get_object_or_404(Circle, pk=pk)
    circle.graduated = not circle.graduated
    circle.save(update_fields=["graduated"])
    dest = "/classes/?graduated=1" if _data(request).get("graduated") else "/classes/"
    return HttpResponseRedirect(dest)


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------
@login_required
@inertia("Announcements/Index")
def announcements_index(request):
    return {
        "announcements": AnnouncementSerializer(
            _announcements_qs(request.user), many=True
        ).data,
        "circles": CircleSerializer(
            _circles_qs(request.user).filter(graduated=False), many=True
        ).data,
    }


@require_POST
@login_required
def announcements_create(request):
    _require_staff(request)
    data = _data(request)
    announcement = Announcement.objects.create(
        title=data.get("title", ""),
        body=data.get("body", ""),
        created_by=request.user,
    )
    announcement.circles.set(_list(data, "circles"))

    from messaging.services import queue_announcement_for_digest

    queue_announcement_for_digest(announcement)
    return HttpResponseRedirect("/announcements/")


@login_required
@inertia("Announcements/Show")
def announcements_show(request, pk):
    announcement = get_object_or_404(_announcements_qs(request.user), pk=pk)
    acks = announcement.acks.select_related("parent").all()
    return {
        "announcement": AnnouncementSerializer(announcement).data,
        "acks": AnnouncementAckSerializer(acks, many=True).data,
    }


# ---------------------------------------------------------------------------
# Updates (nested under a child; no standalone page)
# ---------------------------------------------------------------------------
@require_POST
@login_required
def updates_create(request):
    _require_staff(request)
    data = _data(request)
    child_id = data.get("child")
    update = Update.objects.create(
        child_id=child_id,
        text=data.get("text", ""),
        created_by=request.user,
    )

    from messaging.services import queue_update_for_digest

    queue_update_for_digest(update)
    return HttpResponseRedirect(f"/children/{child_id}/")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@login_required
@inertia("Users")
def users_index(request):
    users = User.objects.all() if _is_staff(request.user) else User.objects.filter(pk=request.user.pk)
    return {
        "users": UserSerializer(users.order_by("username"), many=True).data,
    }


# ---------------------------------------------------------------------------
# Urgent alerts
# ---------------------------------------------------------------------------
@login_required
@inertia("UrgentAlerts")
def urgent_alerts_index(request):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    alerts = UrgentAlert.objects.select_related("created_by").all()
    return {
        "alerts": UrgentAlertSerializer(alerts, many=True).data,
    }


@require_POST
@login_required
def urgent_alerts_create(request):
    _require_staff(request)
    data = _data(request)
    alert = UrgentAlert.objects.create(
        title=data.get("title", ""),
        body=data.get("body", ""),
        created_by=request.user,
    )

    from messaging.tasks import send_urgent_alert

    # Sent synchronously: no Celery/broker in the Cloud Run deployment. Volume is
    # low (staff post alerts manually), so a blocking WhatsApp fan-out is fine.
    send_urgent_alert(alert.id)
    return HttpResponseRedirect("/urgent-alerts/")


# ---------------------------------------------------------------------------
# E-Learning (Courses / Modules / Lessons / Cohorts)
# ---------------------------------------------------------------------------
@login_required
@inertia("ELearning/Index")
def elearning_index(request):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    courses = Course.objects.prefetch_related("modules__lessons").all()
    cohorts = Cohort.objects.select_related("course", "circle").all()
    return {
        "courses": CourseSerializer(courses, many=True).data,
        "cohorts": CohortSerializer(cohorts, many=True).data,
        "circles": CircleSerializer(
            Circle.objects.filter(graduated=False), many=True
        ).data,
    }


@require_POST
@login_required
def courses_create(request):
    _require_staff(request)
    data = _data(request)
    Course.objects.create(
        title=data.get("title", ""),
        description=data.get("description", ""),
    )
    return HttpResponseRedirect("/elearning/")


@login_required
@inertia("ELearning/Course")
def courses_show(request, pk):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    course = get_object_or_404(
        Course.objects.prefetch_related("modules__lessons"), pk=pk
    )
    cohorts = course.cohorts.select_related("circle").prefetch_related(
        "releases__lesson"
    )
    cohort_data = []
    for cohort in cohorts:
        row = CohortSerializer(cohort).data
        row["releases"] = LessonReleaseSerializer(
            cohort.releases.all(), many=True
        ).data
        cohort_data.append(row)
    return {
        "course": CourseSerializer(course).data,
        "cohorts": cohort_data,
        "circles": CircleSerializer(
            Circle.objects.filter(graduated=False), many=True
        ).data,
    }


@require_POST
@login_required
def modules_create(request):
    _require_staff(request)
    data = _data(request)
    course_id = data.get("course")
    Module.objects.create(
        course_id=course_id,
        title=data.get("title", ""),
        order=data.get("order") or 0,
    )
    return HttpResponseRedirect(f"/elearning/courses/{course_id}/")


@require_POST
@login_required
def lessons_create(request):
    _require_staff(request)
    data = _data(request)
    module = get_object_or_404(Module, pk=data.get("module"))
    Lesson.objects.create(
        module=module,
        title=data.get("title", ""),
        description=data.get("description", ""),
        youtube_url=data.get("youtube_url", ""),
        order=data.get("order") or 0,
    )
    return HttpResponseRedirect(f"/elearning/courses/{module.course_id}/")


@require_POST
@login_required
def cohorts_create(request):
    _require_staff(request)
    data = _data(request)
    Cohort.objects.create(
        name=data.get("name", ""),
        course_id=data.get("course"),
        circle_id=data.get("circle"),
        start_date=data.get("start_date") or None,
        send_hour=data.get("send_hour") or 14,
    )
    return HttpResponseRedirect("/elearning/")


@login_required
@inertia("ELearning/Cohort")
def cohorts_show(request, pk):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    cohort = get_object_or_404(
        Cohort.objects.select_related("course", "circle"), pk=pk
    )
    releases = list(cohort.releases.select_related("lesson").order_by("released_at"))
    recipients = list(cohort.circle.members.all())
    completed = set(
        LessonCompletion.objects.filter(release__cohort=cohort).values_list(
            "user_id", "release_id"
        )
    )
    lessons = [
        {"release_id": r.id, "title": r.lesson.title, "released_at": r.released_at}
        for r in releases
    ]
    rows = []
    for user in recipients:
        cells = [(user.pk, r.id) in completed for r in releases]
        rows.append(
            {
                "id": user.pk,
                "name": user.display_name,
                "watched_count": sum(cells),
                "cells": cells,
            }
        )
    return {
        "cohort": CohortSerializer(cohort).data,
        "lessons": lessons,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------
@login_required
@inertia("Messages")
def messages_index(request):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    logs = MessageLog.objects.select_related("recipient").all()
    return {
        "messages": MessageLogSerializer(logs, many=True).data,
    }


# ---------------------------------------------------------------------------
# Payments (school fees)
# ---------------------------------------------------------------------------
@login_required
@inertia("Payments/Index")
def payments_index(request):
    from payments.models import FeePayment
    from payments.serializers import FeePaymentSerializer

    payments = FeePayment.objects.select_related("child").order_by("-created")
    if not _is_staff(request.user):
        # Parents only see fee payments for their own children.
        payments = payments.filter(child__in=_children_qs(request.user))
    created_id = request.GET.get("created")
    created = None
    if created_id:
        payment = payments.filter(pk=created_id).first()
        if payment:
            created = FeePaymentSerializer(payment).data
    return {
        "payments": FeePaymentSerializer(payments, many=True).data,
        "children": ChildSerializer(
            _children_qs(request.user).filter(graduated=False), many=True
        ).data,
        "created": created,
    }


@require_POST
@login_required
def payments_create(request):
    from payments.models import FeePayment

    _require_staff(request)
    data = _data(request)
    payment = FeePayment.objects.create(
        child_id=data.get("child"),
        month=data.get("month", ""),
        amount=data.get("amount") or 0,
    )
    return HttpResponseRedirect(f"/payments/?created={payment.id}")


@require_POST
@login_required
def payments_send_confirmation(request, pk):
    from payments.models import FeePayment
    from payments.services import send_payment_confirmation

    _require_staff(request)
    payment = get_object_or_404(FeePayment, pk=pk)
    send_payment_confirmation(payment)
    return HttpResponseRedirect("/payments/")
