"""Signed, time-limited login tokens for the WhatsApp magic-link flow.

Parents have no password (they are created with ``username=<phone digits>``),
so they get into the app by tapping a link we send over WhatsApp. The link
carries a ``django.core.signing`` token that names the user; the ``magic_login``
view verifies it and starts a normal Django session.

The token is signed with ``SECRET_KEY`` under a dedicated salt and only carries
the user id, so it can't be reused as a token for any other purpose.
"""
from django.core import signing

_SALT = "cocoon.web.magic-login"
DEFAULT_MAX_AGE = 15 * 60  # 15 minutes


def make_login_token(user):
    """Return a signed token that logs ``user`` in when presented to magic_login."""
    return signing.dumps({"uid": user.pk}, salt=_SALT)


def resolve_login_token(token, max_age=DEFAULT_MAX_AGE):
    """Return the User for a valid, unexpired token, or ``None``.

    Returns None on a tampered signature, an expired token, or a uid that no
    longer maps to a user.
    """
    from django.contrib.auth import get_user_model

    try:
        data = signing.loads(token, salt=_SALT, max_age=max_age)
    except signing.BadSignature:
        return None
    uid = data.get("uid")
    if uid is None:
        return None
    return get_user_model().objects.filter(pk=uid).first()
