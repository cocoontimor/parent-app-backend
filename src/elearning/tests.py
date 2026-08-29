"""Tests for the hourly lesson-release drip and its per-cohort send hour."""
from datetime import datetime, timezone as dt_timezone
from unittest import mock

from django.test import TestCase

from children.models import Circle
from elearning.models import Cohort, Course, Lesson, LessonRelease, Module
from elearning.tasks import release_due_lessons

# Asia/Dili is UTC+9, so 05:00 UTC == 14:00 Dili.
NOW_UTC_AT_DILI_1400 = datetime(2026, 8, 29, 5, 0, tzinfo=dt_timezone.utc)


class ReleaseDueLessonsHourTests(TestCase):
    def setUp(self):
        course = Course.objects.create(title="Parenting 101")
        module = Module.objects.create(course=course, title="Week 1", order=0)
        Lesson.objects.create(
            module=module,
            title="Intro",
            youtube_url="https://youtu.be/abc",
            order=0,
            release_offset_days=0,
        )
        circle = Circle.objects.create(name="Family A", type=Circle.Type.FAMILY)
        self.circle = circle
        self.course = course

    def _make_cohort(self, send_hour):
        return Cohort.objects.create(
            name="Cohort",
            course=self.course,
            circle=self.circle,
            start_date="2026-08-29",  # due today in Dili
            send_hour=send_hour,
        )

    @mock.patch("elearning.services.send_lesson_to_recipients")
    @mock.patch("django.utils.timezone.now", return_value=NOW_UTC_AT_DILI_1400)
    def test_releases_when_hour_matches(self, _now, send):
        self._make_cohort(send_hour=14)
        released = release_due_lessons()
        self.assertEqual(released, 1)
        self.assertEqual(LessonRelease.objects.count(), 1)
        self.assertTrue(send.called)

    @mock.patch("elearning.services.send_lesson_to_recipients")
    @mock.patch("django.utils.timezone.now", return_value=NOW_UTC_AT_DILI_1400)
    def test_skips_when_hour_differs(self, _now, send):
        self._make_cohort(send_hour=9)  # not the current Dili hour (14)
        released = release_due_lessons()
        self.assertEqual(released, 0)
        self.assertEqual(LessonRelease.objects.count(), 0)
        self.assertFalse(send.called)
