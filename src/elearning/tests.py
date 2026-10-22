"""Tests for the hourly lesson-release drip and its per-cohort send hour."""
from datetime import datetime, timezone as dt_timezone
from unittest import mock

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from elearning.models import (
    Cohort,
    Course,
    CourseRun,
    Lesson,
    LessonRelease,
    Module,
)
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
        self.course = course

    def _make_cohort(self, send_hour):
        cohort = Cohort.objects.create(name="Cohort")
        return CourseRun.objects.create(
            cohort=cohort,
            course=self.course,
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


class CumulativeReleaseDayTests(TestCase):
    """release_offset_days is a gap from the previous lesson, so release days
    accumulate across modules and lessons in delivery order."""

    def setUp(self):
        from datetime import date

        self.course = Course.objects.create(title="Parenting 101")
        m1 = Module.objects.create(course=self.course, title="Week 1", order=0)
        m2 = Module.objects.create(course=self.course, title="Week 2", order=1)
        # Delivery order A, B, C with gaps 2, 3, 1 -> release days 2, 5, 6.
        self.a = self._lesson(m1, "A", order=0, offset=2)
        self.b = self._lesson(m1, "B", order=1, offset=3)
        self.c = self._lesson(m2, "C", order=0, offset=1)
        self.start = date(2026, 8, 1)

    def _lesson(self, module, title, order, offset):
        return Lesson.objects.create(
            module=module,
            title=title,
            youtube_url="https://youtu.be/x",
            order=order,
            release_offset_days=offset,
        )

    def test_lessons_with_release_day_accumulates(self):
        pairs = [(l.title, day) for l, day in self.course.lessons_with_release_day()]
        self.assertEqual(pairs, [("A", 2), ("B", 5), ("C", 6)])

    def test_due_lessons_uses_cumulative_days(self):
        from datetime import timedelta

        run = CourseRun.objects.create(
            cohort=Cohort.objects.create(name="Cohort"),
            course=self.course,
            start_date=self.start,
            send_hour=14,
        )
        # 5 days in: A (day 2) and B (day 5) are due; C (day 6) is not yet.
        due = run.due_lessons(self.start + timedelta(days=5))
        self.assertEqual([l.title for l in due], ["A", "B"])


class OffsetsToGapsMigrationTests(TransactionTestCase):
    before = [("elearning", "0005_cohort_trainees_courserun")]
    after = [("elearning", "0006_alter_lesson_release_offset_days")]

    def setUp(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        apps = executor.loader.project_state(self.before).apps
        Course = apps.get_model("elearning", "Course")
        Module = apps.get_model("elearning", "Module")
        Lesson = apps.get_model("elearning", "Lesson")
        course = Course.objects.create(title="Weekly")
        week1 = Module.objects.create(course=course, title="W1", order=0)
        week2 = Module.objects.create(course=course, title="W2", order=1)
        # Absolute days after start (the old meaning), across two modules.
        for module, order, day in [(week1, 0, 0), (week1, 1, 7), (week2, 0, 14), (week2, 1, 21)]:
            Lesson.objects.create(
                module=module,
                title=f"day {day}",
                youtube_url="u",
                order=order,
                release_offset_days=day,
            )

    def tearDown(self):
        MigrationExecutor(connection).migrate(
            MigrationExecutor(connection).loader.graph.leaf_nodes()
        )

    def test_absolute_offsets_become_gaps_with_same_release_days(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        apps = executor.loader.project_state(self.after).apps
        Lesson = apps.get_model("elearning", "Lesson")
        gaps = list(
            Lesson.objects.order_by("module__order", "order").values_list(
                "release_offset_days", flat=True
            )
        )
        self.assertEqual(gaps, [0, 7, 7, 7])
        self.assertEqual(
            [day for _, day in Course.objects.get(title="Weekly").lessons_with_release_day()],
            [0, 7, 14, 21],
        )
