import logging

logger = logging.getLogger(__name__)


WATCHED_PAYLOAD_PREFIX = "WATCHED:"


def send_lesson_to_recipients(release):
    """Send a released lesson's YouTube link to every member of the cohort's
    circle, reusing the WhatsApp messaging pipeline. The message carries a
    "Mark as watched" quick-reply button whose payload identifies the release."""
    from messaging.services import send_whatsapp_message

    cohort = release.cohort
    lesson = release.lesson
    body = (
        f"New lesson: {lesson.title}\n"
        f"{cohort.course.title}\n"
        f"Watch: {lesson.youtube_url}"
    )

    recipients = cohort.recipients()
    for user in recipients:
        send_whatsapp_message(
            user,
            template="elearning_lesson",
            body=body,
            variables=[body],
            button_payload=f"{WATCHED_PAYLOAD_PREFIX}{release.id}",
        )

    logger.info(
        "Sent lesson %s (release %s) to %d recipient(s)",
        lesson.id,
        release.id,
        recipients.count(),
    )


def record_completion(from_phone, payload):
    """Record a 'mark as watched' button tap from the WhatsApp webhook.

    ``payload`` looks like ``WATCHED:<release_id>``. Returns the created (or
    existing) LessonCompletion, or None if it can't be matched.
    """
    from django.contrib.auth import get_user_model

    from .models import LessonCompletion, LessonRelease

    if not payload or not payload.startswith(WATCHED_PAYLOAD_PREFIX):
        return None

    release_id = payload[len(WATCHED_PAYLOAD_PREFIX):].strip()
    User = get_user_model()

    try:
        release = LessonRelease.objects.get(id=release_id)
    except LessonRelease.DoesNotExist:
        logger.warning("Completion for unknown release %s", release_id)
        return None

    user = User.objects.filter(username=from_phone).first()
    if user is None:
        logger.warning("Completion from unknown phone %s", from_phone)
        return None

    completion, created = LessonCompletion.objects.get_or_create(
        release=release, user=user
    )
    logger.info(
        "Recorded completion release=%s user=%s (new=%s)",
        release_id,
        user.pk,
        created,
    )
    return completion
