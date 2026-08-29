"""Inertia shared props — data injected into every page's response."""
from inertia import share


def _user_prop(request):
    u = request.user
    if not u.is_authenticated:
        return None
    return {
        "id": u.pk,
        "username": u.username,
        "display_name": u.display_name,
        "is_staff_group": u.groups.filter(name="staff").exists(),
    }


def inertia_share(get_response):
    def middleware(request):
        share(
            request,
            auth=lambda: {"user": _user_prop(request)},
        )
        return get_response(request)

    return middleware
