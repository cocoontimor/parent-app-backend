import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def release_due_lessons():
    """
    Hourly drip job. For each active cohort, release any lessons that have come
    due (by ``release_offset_days`` from ``start_date``) and haven't been
    released yet, sending each lesson's YouTube link to the circle's members.

    Runs every hour; a cohort's due lessons are only sent on the tick whose
    local (Asia/Dili) hour matches that cohort's ``send_hour``, so admins choose
    the delivery hour per cohort.
    """
    from zoneinfo import ZoneInfo

    from django.utils import timezone

    from .models import Cohort, LessonRelease
    from .services import send_lesson_to_recipients

    now_local = timezone.now().astimezone(ZoneInfo("Asia/Dili"))
    today = now_local.date()
    current_hour = now_local.hour
    released_total = 0

    cohorts = Cohort.objects.filter(active=True).select_related("course", "circle")
    for cohort in cohorts:
        if cohort.send_hour != current_hour:
            continue
        already = set(cohort.releases.values_list("lesson_id", flat=True))

        for lesson in cohort.due_lessons(today):
            if lesson.id in already:
                continue
            release = LessonRelease.objects.create(cohort=cohort, lesson=lesson)
            send_lesson_to_recipients(release)
            released_total += 1

    logger.info("release_due_lessons: released %d lesson(s)", released_total)
    return released_total
