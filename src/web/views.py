"""
Inertia (Svelte) views for the Cocoon admin. Replaces the standalone Next.js
`app-admin` frontend: pages are rendered server-side with props instead of the
client fetching a DRF API. Auth is session-based (django.contrib.auth); writes
are gated to the "staff" group, mirroring the old IsStaffGroupOrReadOnly.

Read props reuse the existing DRF serializers so the shape stays identical to
what the React pages consumed.
"""
import json
import logging
import re
from zoneinfo import ZoneInfo

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Max, Q, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from inertia import inertia, render

from announcements.models import Announcement
from announcements.serializers import AnnouncementSerializer
from attendance.models import Attendance
from children.models import Child, Circle, Member
from children.serializers import ChildSerializer, CircleSerializer
from elearning.models import (
    Cohort,
    Course,
    CourseRun,
    Lesson,
    LessonCompletion,
    Module,
)
from elearning.serializers import (
    CohortSerializer,
    CourseRunSerializer,
    CourseSerializer,
)
from messaging.models import DigestQueue, MessageLog
from messaging.serializers import MessageLogSerializer
from messaging.services import queue_announcement_for_digest, queue_update_for_digest
from messaging.tasks import send_urgent_alert
from payments.models import FeePayment
from payments.serializers import FeePaymentSerializer
from payments.services import send_payment_confirmation
from photos.models import Photo
from updates.models import Update, UrgentAlert
from updates.serializers import UpdateSerializer, UrgentAlertSerializer
from users.models import User
from users.serializers import UserSerializer

from .tokens import resolve_login_token


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


def _is_teacher(user):
    return user.groups.filter(name="teacher").exists()


def _can_edit_child(user, child):
    """Admins manage any child; teachers any child in a classroom (they swap
    rooms to cover staffing, so not just the ones they teach). Parents cannot
    edit."""
    if _is_staff(user):
        return True
    if _is_teacher(user):
        return child.circles.filter(type=Circle.Type.CLASSROOM).exists()
    return False


def _require_edit_child(request, child):
    if not _can_edit_child(request.user, child):
        raise PermissionDenied("Not allowed for this child.")


def _can_edit_circle(user, circle):
    """Admins manage any circle; teachers any classroom."""
    if _is_staff(user):
        return True
    if _is_teacher(user):
        return circle.type == Circle.Type.CLASSROOM
    return False


def _require_edit_circle(request, circle):
    if not _can_edit_circle(request.user, circle):
        raise PermissionDenied("Not allowed for this class.")


def _data(request):
    """Inertia posts JSON when there are no files, form-encoded otherwise."""
    ctype = request.content_type or ""
    if "application/json" in ctype:
        try:
            return json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return {}
    return request.POST


def _parse_date(value):
    """A YYYY-MM-DD string as a date, or None if missing or not a real date."""
    try:
        return parse_date(value or "")
    except ValueError:
        return None


def _class_teachers():
    """Users who can be assigned as a class's teachers."""
    return User.objects.filter(groups__name__in=["staff", "teacher"]).distinct()


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
    if _is_teacher(user):
        # Teachers see the children in every classroom.
        return Child.objects.filter(circles__type="classroom").distinct()
    return Child.objects.filter(
        circles__type="family", circles__members=user
    ).distinct()


def _circles_qs(user):
    if _is_staff(user):
        return Circle.objects.all()
    if _is_teacher(user):
        return Circle.objects.filter(
            Q(members=user) | Q(type=Circle.Type.CLASSROOM)
        ).distinct()
    return Circle.objects.filter(members=user)


def _announcements_qs(user):
    if _is_staff(user):
        return Announcement.objects.all()
    visible = Q(circles__isnull=True) | Q(circles__members=user)
    if _is_teacher(user):
        visible |= Q(circles__type=Circle.Type.CLASSROOM)
    return Announcement.objects.filter(visible).distinct()


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
    children = _children_qs(request.user).filter(graduation_date__isnull=True)
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
    q = (request.GET.get("q") or "").strip()
    children = (
        _children_qs(request.user)
        .filter(graduation_date__isnull=not graduated)
        .prefetch_related("circles__member_records__user")
        .order_by("name")
    )
    if q:
        # Match on the child's own name, a parent (family-circle member's
        # name or phone/username), or a classroom name.
        children = children.filter(
            Q(name__icontains=q)
            | Q(circles__type="family", circles__members__full_name__icontains=q)
            | Q(circles__type="family", circles__members__username__icontains=q)
            | Q(circles__type="classroom", circles__name__icontains=q)
        ).distinct()

    paginator = Paginator(children, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "children": [_child_row(c) for c in page_obj],
        "graduated": graduated,
        "q": q,
        "pagination": {
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "count": paginator.count,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
        },
    }


def _child_row(child):
    """Child row for the index, enriched with its parents (family-circle
    members) and classes (classroom circles) for display and search."""
    parents = []
    classes = []
    for circle in child.circles.all():
        if circle.type == Circle.Type.CLASSROOM:
            classes.append(circle.name)
        else:
            for mr in circle.member_records.all():
                parents.append(mr.user.display_name)
    data = ChildSerializer(child).data
    data["parents"] = parents
    data["classes"] = classes
    return data


@require_POST
@login_required
def children_graduate(request, pk):
    child = get_object_or_404(Child, pk=pk)
    _require_edit_child(request, child)
    child.graduation_date = None if child.graduation_date else timezone.now().date()
    child.save(update_fields=["graduation_date"])
    # Stay on whichever view (current/graduated) the action came from.
    dest = "/children/?graduated=1" if _data(request).get("graduated") else "/children/"
    return HttpResponseRedirect(dest)


def _apply_parents(circle, rows):
    """Create/update parent users and their memberships in a family circle from
    a list of {full_name, relationship, number} rows (capped at 4). Returns the
    ids of the parent users that were kept, so callers can prune the rest."""
    parent_group, _ = Group.objects.get_or_create(name="parent")
    kept = []
    for row in rows[:4]:
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
        kept.append(parent.pk)
    return kept


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

    _apply_parents(circle, _list(data, "parents"))

    return HttpResponseRedirect("/children/")


@require_POST
@login_required
@transaction.atomic
def children_family_update(request, pk):
    """Add or edit the parents in a child's family circle. Creates the family
    circle on first use, then syncs its parents to the posted list."""
    child = get_object_or_404(Child, pk=pk)
    _require_edit_child(request, child)
    data = _data(request)

    circle = child.circles.filter(type=Circle.Type.FAMILY).first()
    if circle is None:
        circle = Circle.objects.create(
            name=f"{child.name} Family" if child.name else "Family",
            type=Circle.Type.FAMILY,
        )
        circle.children.add(child)

    kept = _apply_parents(circle, _list(data, "parents"))
    # Drop parents that were removed in the edit (membership only; the user
    # account stays in case they belong to another family).
    circle.member_records.exclude(user_id__in=kept).delete()

    return HttpResponseRedirect(f"/children/{child.pk}/")


@require_POST
@login_required
def children_update(request, pk):
    child = get_object_or_404(Child, pk=pk)
    _require_edit_child(request, child)
    data = _data(request)
    child.name = (data.get("name") or "").strip() or child.name
    child.date_of_birth = data.get("date_of_birth") or None
    child.save(update_fields=["name", "date_of_birth"])
    return HttpResponseRedirect(f"/children/{child.pk}/")


@login_required
@inertia("Children/Show")
def children_show(request, pk):
    child = get_object_or_404(_children_qs(request.user), pk=pk)
    family = None
    classes = []
    for circle in child.circles.prefetch_related("member_records__user").all():
        if circle.type == Circle.Type.FAMILY:
            # One family circle per child by convention; take the first.
            if family is None:
                family = {
                    "id": circle.id,
                    "name": circle.name,
                    "parents": [
                        {
                            "id": mr.user.pk,
                            "name": mr.user.display_name,
                            "full_name": mr.user.full_name,
                            "number": mr.user.username,
                            "relationship": mr.relationship,
                        }
                        for mr in circle.member_records.all()
                    ],
                }
        else:
            classes.append(
                {
                    "id": circle.id,
                    "name": circle.name,
                    "teachers": [
                        mr.user.display_name for mr in circle.member_records.all()
                    ],
                }
            )
    updates = (
        Update.objects.select_related("created_by")
        .filter(child=child)
        .order_by("-created")
    )
    payments = FeePayment.objects.filter(child=child).order_by("-created")
    # Attendance history, paginated (its own ?att_page= so it doesn't disturb
    # the other tabs).
    att_qs = Attendance.objects.filter(child=child).order_by("-date")
    att_page = Paginator(att_qs, 10).get_page(request.GET.get("att_page"))
    return {
        "child": ChildSerializer(child).data,
        "family": family,
        "classes": classes,
        "updates": UpdateSerializer(updates, many=True).data,
        "payments": FeePaymentSerializer(payments, many=True).data,
        "attendance": [
            {
                "id": a.id,
                "date": a.date.isoformat(),
                "status": a.status,
            }
            for a in att_page
        ],
        "attendance_pagination": {
            "page": att_page.number,
            "num_pages": att_page.paginator.num_pages,
            "count": att_page.paginator.count,
            "has_previous": att_page.has_previous(),
            "has_next": att_page.has_next(),
        },
    }


@login_required
def parents_search(request):
    """Typeahead for the Edit Family picker: search over existing parent
    accounts by name or number (staff or teachers). At most 10 matches."""
    if not (_is_staff(request.user) or _is_teacher(request.user)):
        raise PermissionDenied("Staff or teacher required.")
    q = (request.GET.get("q") or "").strip()
    parents = User.objects.filter(groups__name="parent")
    if q:
        digits = re.sub(r"\D", "", q)
        cond = Q(full_name__icontains=q)
        if digits:
            cond |= Q(username__contains=digits)
        parents = parents.filter(cond)
    parents = parents.order_by("full_name", "username")[:10]
    return JsonResponse(
        {"parents": [{"full_name": u.full_name, "number": u.username} for u in parents]}
    )


# ---------------------------------------------------------------------------
# Classes (Circle model/logic, exposed under /classes/)
# ---------------------------------------------------------------------------
@login_required
@inertia("Classes")
def classes_index(request):
    graduated = request.GET.get("graduated") == "1"
    classes = (
        _circles_qs(request.user)
        .filter(type=Circle.Type.CLASSROOM, graduated=graduated)
        .prefetch_related("members", "children")
    )
    # Teacher-eligible users for the class picker (staff and teachers).
    # Available to admins and teachers (who may edit any class).
    users = (
        _class_teachers()
        if _is_staff(request.user) or _is_teacher(request.user)
        else User.objects.none()
    )
    # Children currently in an active class. The picker uses this to hide them
    # when creating, and to allow only *this* class's own when editing.
    assigned_child_ids = list(
        Child.objects.filter(
            circles__type=Circle.Type.CLASSROOM, circles__graduated=False
        )
        .values_list("pk", flat=True)
        .distinct()
    )
    return {
        "circles": CircleSerializer(classes, many=True).data,
        "children": ChildSerializer(
            _children_qs(request.user).filter(graduation_date__isnull=True), many=True
        ).data,
        "users": UserSerializer(users, many=True).data,
        "assigned_child_ids": assigned_child_ids,
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
    for user_id in _class_teachers().filter(pk__in=_list(data, "members")).values_list(
        "pk", flat=True
    ):
        Member.objects.update_or_create(
            circle=circle,
            user_id=user_id,
            defaults={"relationship": Member.Relationship.TEACHER},
        )
    # Guard against a stale picker: drop any submitted child already in an
    # active class (mirrors the exclusion in classes_index).
    in_active_class = Circle.objects.filter(
        type=Circle.Type.CLASSROOM, graduated=False
    ).values("children")
    eligible = (
        Child.objects.filter(pk__in=_list(data, "children"), graduation_date__isnull=True)
        .exclude(pk__in=in_active_class)
    )
    circle.children.set(eligible)
    return HttpResponseRedirect("/classes/")


@require_POST
@login_required
def classes_update(request, pk):
    circle = get_object_or_404(Circle, pk=pk, type=Circle.Type.CLASSROOM)
    _require_edit_circle(request, circle)
    data = _data(request)

    name = (data.get("name") or "").strip()
    if name:
        circle.name = name
        circle.save(update_fields=["name"])

    # Sync teachers: add/keep the submitted members, drop the rest.
    kept = []
    for user_id in _class_teachers().filter(pk__in=_list(data, "members")).values_list(
        "pk", flat=True
    ):
        Member.objects.update_or_create(
            circle=circle,
            user_id=user_id,
            defaults={"relationship": Member.Relationship.TEACHER},
        )
        kept.append(user_id)
    circle.member_records.exclude(user_id__in=kept).delete()

    # Sync children: allow only children free or already in THIS class
    # (i.e. exclude those held by some *other* active class).
    in_other_active_class = (
        Circle.objects.filter(type=Circle.Type.CLASSROOM, graduated=False)
        .exclude(pk=circle.pk)
        .values("children")
    )
    eligible = (
        Child.objects.filter(pk__in=_list(data, "children"), graduation_date__isnull=True)
        .exclude(pk__in=in_other_active_class)
    )
    circle.children.set(eligible)
    return HttpResponseRedirect("/classes/")


@require_POST
@login_required
def classes_graduate(request, pk):
    circle = get_object_or_404(Circle, pk=pk)
    _require_edit_circle(request, circle)
    circle.graduated = not circle.graduated
    circle.save(update_fields=["graduated"])
    dest = "/classes/?graduated=1" if _data(request).get("graduated") else "/classes/"
    return HttpResponseRedirect(dest)


@login_required
@inertia("Classes/Attendance")
def classes_attendance(request, pk):
    # Scoped by _circles_qs: admins and teachers get any class, and
    # parents match no classroom (404), so no separate role gate is needed.
    circle = get_object_or_404(
        _circles_qs(request.user), pk=pk, type=Circle.Type.CLASSROOM
    )
    # Default to today (Asia/Dili; settings.TIME_ZONE is UTC) so the sheet
    # opens on the current session. An invalid date falls back to today too.
    date_str = (
        _parse_date(request.GET.get("date"))
        or timezone.localdate(timezone=ZoneInfo("Asia/Dili"))
    ).isoformat()
    children = circle.children.order_by("name")
    marked = {
        a.child_id: a.status
        for a in Attendance.objects.filter(circle=circle, date=date_str)
    }
    roster = [
        {"id": c.id, "name": c.name, "status": marked.get(c.id, "present")}
        for c in children
    ]
    return {
        "circle": {"id": circle.id, "name": circle.name},
        "date": date_str,
        "roster": roster,
    }


@require_POST
@login_required
def classes_attendance_save(request, pk):
    circle = get_object_or_404(Circle, pk=pk, type=Circle.Type.CLASSROOM)
    _require_edit_circle(request, circle)
    data = _data(request)
    date = _parse_date(data.get("date"))
    if not date:
        raise PermissionDenied("A valid date is required.")
    date_str = date.isoformat()
    valid_ids = set(circle.children.values_list("pk", flat=True))
    valid_status = set(Attendance.Status.values)
    for entry in _list(data, "roster"):
        child_id = entry.get("id")
        status = entry.get("status")
        if child_id not in valid_ids or status not in valid_status:
            continue
        Attendance.objects.update_or_create(
            child_id=child_id,
            circle=circle,
            date=date_str,
            defaults={"status": status, "marked_by": request.user},
        )
    return HttpResponseRedirect(f"/classes/{circle.pk}/attendance/?date={date_str}")


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
            _circles_qs(request.user)
            .filter(graduated=False)
            .prefetch_related("members", "children"),
            many=True,
        ).data,
    }


@require_POST
@login_required
def announcements_create(request):
    data = _data(request)
    circle_ids = [str(c) for c in _list(data, "circles")]
    if not _is_staff(request.user):
        # Teachers may announce to classrooms, but not center-wide.
        if not _is_teacher(request.user):
            raise PermissionDenied("Staff or teacher required.")
        allowed = {
            str(pk)
            for pk in _circles_qs(request.user)
            .filter(graduated=False)
            .values_list("pk", flat=True)
        }
        if not circle_ids or any(c not in allowed for c in circle_ids):
            raise PermissionDenied("Teachers must target classes.")
    announcement = Announcement.objects.create(
        title=data.get("title", ""),
        body=data.get("body", ""),
        created_by=request.user,
    )
    announcement.circles.set(circle_ids)

    for image in request.FILES.getlist("photos"):
        Photo.objects.create(owner=announcement, image=image)

    queue_announcement_for_digest(announcement)
    return HttpResponseRedirect("/announcements/")


@login_required
@inertia("Announcements/Show")
def announcements_show(request, pk):
    announcement = get_object_or_404(_announcements_qs(request.user), pk=pk)
    # A parent acknowledged this announcement if the digest that delivered it
    # was acked; that ack timestamp lives on the linked MessageLog.
    acked = DigestQueue.objects.filter(
        item_type=DigestQueue.ItemType.ANNOUNCEMENT,
        item_id=announcement.id,
        message_log__acknowledged_at__isnull=False,
    ).select_related("recipient", "message_log")
    acks = [
        {
            "id": item.id,
            "parent": item.recipient_id,
            "parent_name": item.recipient.display_name,
            "created": item.message_log.acknowledged_at,
        }
        for item in acked
    ]
    return {
        "announcement": AnnouncementSerializer(announcement).data,
        "acks": acks,
    }


# ---------------------------------------------------------------------------
# Updates (nested under a child; no standalone page)
# ---------------------------------------------------------------------------
@require_POST
@login_required
def updates_create(request):
    data = _data(request)
    child = get_object_or_404(Child, pk=data.get("child"))
    _require_edit_child(request, child)
    child_id = child.pk
    update = Update.objects.create(
        child=child,
        text=data.get("text", ""),
        created_by=request.user,
    )

    for image in request.FILES.getlist("photos"):
        Photo.objects.create(owner=update, image=image)

    queue_update_for_digest(update)
    return HttpResponseRedirect(f"/children/{child_id}/")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
@login_required
@inertia("Users")
def users_index(request):
    return {
        "users": UserSerializer(_users_qs(request.user), many=True).data,
    }


def _users_qs(user):
    if _is_staff(user):
        users = User.objects.all()
    elif _is_teacher(user):
        # Teachers see the parents of classroom children (their contact list).
        users = User.objects.filter(
            circles__type="family", circles__children__in=_children_qs(user)
        ).distinct()
    else:
        users = User.objects.filter(pk=user.pk)
    return users.prefetch_related("groups", "cohorts").order_by("username")


# Staff, teacher, and trainee accounts are creatable here; normal (parent)
# users are provisioned from the family circle by phone number.
CREATABLE_ROLES = {"staff", "teacher", "trainee"}
# These sign in with a username + password (trainees/parents are phone-based).
PASSWORD_ROLES = {"staff", "teacher"}


@require_POST
@login_required
def users_create(request):
    _require_staff(request)
    data = _data(request)
    role = data.get("role") or ""
    if role not in CREATABLE_ROLES:
        raise PermissionDenied("Only staff, teacher, and trainee users can be created.")

    # Trainees are phone-based (like parents): the phone is their username and
    # they log in via WhatsApp magic link, so no password. Staff and teachers
    # sign in with a username + password. Neither has an email.
    username = (data.get("username") or "").strip()
    if role == "trainee":
        # Phone in, canonical digits out (670XXXXXXXX) — matches parents and
        # what WhatsApp posts back on its webhook.
        username = re.sub(r"\D", "", username)
    password = data.get("password") or ""

    errors = {}
    if not username:
        errors["username"] = (
            "Phone is required." if role == "trainee" else "Username is required."
        )
    elif User.objects.filter(username=username).exists():
        label = "phone" if role == "trainee" else "username"
        errors["username"] = f"That {label} is already taken."
    if role in PASSWORD_ROLES and not password:
        errors["password"] = "Password is required."
    if errors:
        return render(
            request,
            "Users",
            props={
                "users": UserSerializer(_users_qs(request.user), many=True).data,
                "errors": errors,
            },
        )

    group, _ = Group.objects.get_or_create(name=role)
    user = User.objects.create(
        username=username,
        full_name=(data.get("full_name") or "").strip(),
    )
    if role in PASSWORD_ROLES:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save(update_fields=["password"])
    user.groups.add(group)
    return HttpResponseRedirect("/users/")


# ---------------------------------------------------------------------------
# Urgent alerts
# ---------------------------------------------------------------------------
@login_required
@inertia("UrgentAlerts")
def urgent_alerts_index(request):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    alerts = UrgentAlert.objects.select_related("created_by").annotate(
        recipient_count=Count("message_logs", distinct=True),
        ack_count=Count(
            "message_logs",
            filter=Q(message_logs__acknowledged_at__isnull=False),
            distinct=True,
        ),
    )
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

    # Sent synchronously: no Celery/broker in the Cloud Run deployment. Volume is
    # low (staff post alerts manually), so a blocking WhatsApp fan-out is fine.
    send_urgent_alert(alert.id)
    return HttpResponseRedirect("/urgent-alerts/")


# ---------------------------------------------------------------------------
# E-Learning (Courses / Modules / Lessons / Cohorts)
# ---------------------------------------------------------------------------
@login_required
def elearning_index(request):
    # E-learning is admin-only; bounce non-staff before the courses redirect.
    denied = _deny_non_staff(request)
    if denied:
        return denied
    return HttpResponseRedirect("/elearning/courses/")


@login_required
@inertia("ELearning/Courses")
def courses_index(request):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    courses = Course.objects.prefetch_related("modules__lessons").all()
    return {
        "courses": CourseSerializer(courses, many=True).data,
    }


@login_required
@inertia("ELearning/Cohorts")
def cohorts_index(request):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    cohorts = Cohort.objects.prefetch_related("runs__course", "members").all()
    trainees = (
        User.objects.filter(groups__name="trainee")
        .prefetch_related("groups", "cohorts")
        .order_by("username")
    )
    return {
        "cohorts": CohortSerializer(cohorts, many=True).data,
        "trainees": UserSerializer(trainees, many=True).data,
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
    return HttpResponseRedirect("/elearning/courses/")


@login_required
@inertia("ELearning/Course")
def courses_show(request, pk):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    course = get_object_or_404(
        Course.objects.prefetch_related("modules__lessons"), pk=pk
    )
    return {
        "course": CourseSerializer(course).data,
    }


@require_POST
@login_required
def courses_update(request, pk):
    _require_staff(request)
    course = get_object_or_404(Course, pk=pk)
    data = _data(request)
    course.title = (data.get("title") or "").strip() or course.title
    course.description = data.get("description", "")
    course.save(update_fields=["title", "description"])
    return HttpResponseRedirect(f"/elearning/courses/{course.pk}/")


def _next_order(siblings):
    """One past the highest sibling order. A count would collide once a
    sibling has been soft-deleted and left a gap."""
    highest = siblings.aggregate(m=Max("order"))["m"]
    return 0 if highest is None else highest + 1


@require_POST
@login_required
def modules_create(request):
    _require_staff(request)
    data = _data(request)
    course_id = data.get("course")
    Module.objects.create(
        course_id=course_id,
        title=data.get("title", ""),
        # New modules append to the end; order is managed via reorder arrows.
        order=_next_order(Module.objects.filter(course_id=course_id)),
    )
    return HttpResponseRedirect(f"/elearning/courses/{course_id}/")


@require_POST
@login_required
def modules_update(request, pk):
    _require_staff(request)
    module = get_object_or_404(Module, pk=pk)
    data = _data(request)
    module.title = (data.get("title") or "").strip() or module.title
    module.save(update_fields=["title"])
    return HttpResponseRedirect(f"/elearning/courses/{module.course_id}/")


@require_POST
@login_required
def modules_delete(request, pk):
    """Soft-delete a module (and, implicitly, its lessons drop out of the
    course via the ``module__deleted`` filter)."""
    _require_staff(request)
    module = get_object_or_404(Module, pk=pk)
    module.deleted = timezone.now()
    module.save(update_fields=["deleted"])
    return HttpResponseRedirect(f"/elearning/courses/{module.course_id}/")


@require_POST
@login_required
@transaction.atomic
def modules_reorder(request, pk):
    """Swap a module with its neighbour (up/down), then normalise orders."""
    _require_staff(request)
    module = get_object_or_404(Module, pk=pk)
    direction = _data(request).get("direction")
    siblings = list(module.course.modules.all())
    idx = [m.pk for m in siblings].index(module.pk)
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(siblings):
        siblings[idx], siblings[swap] = siblings[swap], siblings[idx]
        for i, m in enumerate(siblings):
            if m.order != i:
                m.order = i
                m.save(update_fields=["order"])
    return HttpResponseRedirect(f"/elearning/courses/{module.course_id}/")


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
        # New lessons append to the end; order is managed via reorder arrows.
        order=_next_order(module.lessons.all()),
        release_offset_days=data.get("release_offset_days") or 0,
    )
    return HttpResponseRedirect(f"/elearning/courses/{module.course_id}/")


@require_POST
@login_required
def lessons_update(request, pk):
    _require_staff(request)
    lesson = get_object_or_404(Lesson, pk=pk)
    data = _data(request)
    lesson.title = (data.get("title") or "").strip() or lesson.title
    lesson.description = data.get("description", "")
    lesson.youtube_url = (data.get("youtube_url") or "").strip() or lesson.youtube_url
    lesson.release_offset_days = data.get("release_offset_days") or 0
    lesson.save(
        update_fields=[
            "title", "description", "youtube_url", "release_offset_days"
        ]
    )
    return HttpResponseRedirect(f"/elearning/courses/{lesson.module.course_id}/")


@require_POST
@login_required
def lessons_delete(request, pk):
    _require_staff(request)
    lesson = get_object_or_404(Lesson, pk=pk)
    lesson.deleted = timezone.now()
    lesson.save(update_fields=["deleted"])
    return HttpResponseRedirect(f"/elearning/courses/{lesson.module.course_id}/")


@require_POST
@login_required
@transaction.atomic
def lessons_reorder(request, pk):
    """Swap a lesson with its neighbour (up/down) within its module."""
    _require_staff(request)
    lesson = get_object_or_404(Lesson, pk=pk)
    direction = _data(request).get("direction")
    siblings = list(lesson.module.lessons.all())
    idx = [l.pk for l in siblings].index(lesson.pk)
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(siblings):
        siblings[idx], siblings[swap] = siblings[swap], siblings[idx]
        for i, l in enumerate(siblings):
            if l.order != i:
                l.order = i
                l.save(update_fields=["order"])
    return HttpResponseRedirect(f"/elearning/courses/{lesson.module.course_id}/")


@require_POST
@login_required
def cohorts_create(request):
    """Create a cohort by picking trainees. No course yet — a course is added
    and started later via a CourseRun on the cohort's page."""
    _require_staff(request)
    data = _data(request)
    cohort = Cohort.objects.create(name=data.get("name", ""))
    member_ids = _list(data, "members")
    if member_ids:
        cohort.members.set(
            User.objects.filter(pk__in=member_ids, groups__name="trainee")
        )
    return HttpResponseRedirect(f"/elearning/cohorts/{cohort.pk}/")


@require_POST
@login_required
@transaction.atomic
def runs_create(request, pk):
    """Add a course to a cohort and start it running: opens a new CourseRun
    whose start_date/send_hour drive the drip. Any prior run is deactivated
    and left as a record, so trainees only receive the new course."""
    _require_staff(request)
    cohort = get_object_or_404(Cohort, pk=pk)
    data = _data(request)
    course = Course.objects.filter(pk=data.get("course")).first()
    start_date = _parse_date(data.get("start_date"))
    if not course or not start_date:
        raise PermissionDenied("A course and a valid start date are required.")
    try:
        send_hour = int(data.get("send_hour"))
    except (TypeError, ValueError):
        send_hour = 14
    if not 0 <= send_hour <= 23:
        send_hour = 14
    cohort.runs.filter(active=True).update(active=False)
    CourseRun.objects.create(
        cohort=cohort,
        course=course,
        start_date=start_date,
        send_hour=send_hour,
    )
    return HttpResponseRedirect(f"/elearning/cohorts/{cohort.pk}/")


@login_required
@inertia("ELearning/Cohort")
def cohorts_show(request, pk):
    denied = _deny_non_staff(request)
    if denied:
        return denied
    cohort = get_object_or_404(Cohort.objects.prefetch_related("members"), pk=pk)
    runs = list(cohort.runs.select_related("course").all())
    # The current run (active, else latest) is highlighted in the runs table.
    current = next((r for r in runs if r.active), runs[0] if runs else None)

    recipients = list(cohort.members.all())
    # One watched grid per run/course, so a cohort's completion is visible for
    # every course it has run — not just the current one.
    watched_by_course = []
    for run in runs:
        releases = list(run.releases.select_related("lesson").order_by("released_at"))
        if not releases:
            continue
        completed = set(
            LessonCompletion.objects.filter(release__run=run).values_list(
                "user_id", "release_id"
            )
        )
        lessons = [
            {"release_id": r.id, "title": r.lesson.title, "released_at": r.released_at}
            for r in releases
        ]
        rows = []
        for user in recipients:
            cells = [(user.pk, l["release_id"]) in completed for l in lessons]
            rows.append(
                {
                    "id": user.pk,
                    "name": user.display_name,
                    "watched_count": sum(cells),
                    "cells": cells,
                }
            )
        watched_by_course.append(
            {
                "run_id": run.id,
                "course_title": run.course.title,
                "active": run.active,
                "start_date": run.start_date,
                "lessons": lessons,
                "rows": rows,
            }
        )
    return {
        "cohort": CohortSerializer(cohort).data,
        "runs": CourseRunSerializer(runs, many=True).data,
        "current_run_id": current.id if current else None,
        "courses": CourseSerializer(Course.objects.all(), many=True).data,
        "watched_by_course": watched_by_course,
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
def _payment_row(payment):
    """Payment row for the index, enriched with the child's parents (family-
    circle members) for display and search."""
    parents = []
    for circle in payment.child.circles.all():
        if circle.type == Circle.Type.FAMILY:
            for mr in circle.member_records.all():
                parents.append(mr.user.display_name)
    data = FeePaymentSerializer(payment).data
    data["parents"] = parents
    return data


@login_required
@inertia("Payments/Index")
def payments_index(request):
    q = (request.GET.get("q") or "").strip()
    month = (request.GET.get("month") or "").strip()
    # Sorted by the month the payment covers (newest first), then by logged date.
    payments = FeePayment.objects.select_related("child").prefetch_related(
        "child__circles__member_records__user"
    ).order_by("-month", "-created")
    if not _is_staff(request.user):
        # Parents and teachers only see fee payments for their own children.
        payments = payments.filter(child__in=_children_qs(request.user))
    # Distinct months available to this user, for the filter dropdown. Computed
    # before the search/month filters so the options stay stable.
    months = list(
        payments.exclude(month="")
        .order_by("-month")
        .values_list("month", flat=True)
        .distinct()
    )
    if month:
        payments = payments.filter(month=month)
    if q:
        # Match on the child's name, or a parent (family-circle member's name
        # or phone/username).
        payments = payments.filter(
            Q(child__name__icontains=q)
            | Q(child__circles__type="family", child__circles__members__full_name__icontains=q)
            | Q(child__circles__type="family", child__circles__members__username__icontains=q)
        ).distinct()

    # Status breakdown for the current month/search scope, before the status
    # filter narrows the list — powers the "X of Y paid" summary.
    summary = payments.aggregate(
        total=Count("id", distinct=True),
        paid=Count("id", distinct=True, filter=Q(status="paid")),
        due=Count("id", distinct=True, filter=Q(status="pending")),
        waived=Count("id", distinct=True, filter=Q(status="waived")),
        # Fees summed across non-graduated (active) students only.
        active_amount=Sum("amount", filter=Q(child__graduation_date__isnull=True)),
    )

    status_filter = (request.GET.get("status") or "").strip()
    if status_filter in FeePayment.Status.values:
        payments = payments.filter(status=status_filter)

    paginator = Paginator(payments, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return {
        "payments": [_payment_row(p) for p in page_obj],
        "q": q,
        "month": month,
        "months": months,
        "status": status_filter,
        "summary": summary,
        "pagination": {
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "count": paginator.count,
            "has_previous": page_obj.has_previous(),
            "has_next": page_obj.has_next(),
        },
    }


@require_POST
@login_required
def payments_create(request):
    data = _data(request)
    child = get_object_or_404(Child, pk=data.get("child"))
    _require_edit_child(request, child)
    # A manual entry is a received payment; upsert so it fills any pending
    # invoice already generated for that month (unique per child+month).
    payment, _ = FeePayment.objects.update_or_create(
        child=child,
        month=data.get("month", ""),
        defaults={
            "amount": data.get("amount") or 0,
            "status": FeePayment.Status.PAID,
            "paid_at": timezone.now(),
            "marked_by": request.user,
        },
    )
    return HttpResponseRedirect(f"/children/{payment.child_id}/")


@require_POST
@login_required
def payments_generate(request):
    """Admin: generate a pending fee invoice for every active child that
    doesn't already have one for the given month, at a flat amount."""
    _require_staff(request)
    data = _data(request)
    month = (data.get("month") or "").strip()
    if not month:
        return HttpResponseRedirect("/payments/")
    amount = data.get("amount") or 0
    active = Child.objects.filter(graduation_date__isnull=True)
    have = set(
        FeePayment.objects.filter(month=month, child__in=active).values_list(
            "child_id", flat=True
        )
    )
    FeePayment.objects.bulk_create(
        [
            FeePayment(
                child=c,
                month=month,
                amount=amount,
                status=FeePayment.Status.PENDING,
            )
            for c in active
            if c.id not in have
        ]
    )
    return HttpResponseRedirect(f"/payments/?month={month}")


@require_POST
@login_required
def payments_mark(request, pk):
    """Mark an invoice paid / waived / pending. Scoped like child edits."""
    payment = get_object_or_404(FeePayment, pk=pk)
    _require_edit_child(request, payment.child)
    data = _data(request)
    status = data.get("status")
    if status not in FeePayment.Status.values:
        raise PermissionDenied("Invalid status.")
    was_paid = payment.status == FeePayment.Status.PAID
    payment.status = status
    if status == FeePayment.Status.PAID:
        payment.paid_at = timezone.now()
        payment.marked_by = request.user
    else:
        payment.paid_at = None
        payment.marked_by = request.user
    payment.save(update_fields=["status", "paid_at", "marked_by"])
    # Newly marking a receipt paid sends the parents a WhatsApp confirmation.
    if status == FeePayment.Status.PAID and not was_paid:
        try:
            send_payment_confirmation(payment)
        except Exception:
            logging.getLogger(__name__).exception(
                "Payment receipt send failed for %s", payment.id
            )
    # Return to the page the action came from (internal paths only).
    nxt = data.get("next") or ""
    if not nxt.startswith("/") or not url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        nxt = f"/children/{payment.child_id}/"
    return HttpResponseRedirect(nxt)


@require_POST
@login_required
def payments_send_confirmation(request, pk):
    payment = get_object_or_404(FeePayment, pk=pk)
    _require_edit_child(request, payment.child)
    send_payment_confirmation(payment)
    return HttpResponseRedirect(f"/children/{payment.child_id}/")
