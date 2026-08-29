from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from utils.models import BaseModel


class Course(BaseModel):
    """A curriculum / program of study (the top-level "topic").

    A Course groups ordered Modules, each of which groups ordered Lessons.
    Cohorts drip a course's lessons to a circle's members over time.
    """

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elearning_courses"
        ordering = ["title"]

    def __str__(self):
        return self.title

    def ordered_lessons(self):
        """All lessons in delivery order: by module order, then lesson order."""
        return Lesson.objects.filter(module__course=self).order_by(
            "module__order", "order"
        )


class Module(BaseModel):
    """An ordered section within a Course (e.g. "Week 1: Foundations")."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="modules",
    )
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "elearning_modules"
        ordering = ["order", "created"]

    def __str__(self):
        return f"{self.course.title} / {self.title}"


class Lesson(BaseModel):
    """A single learning unit: one YouTube video within a Module."""

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    youtube_url = models.URLField()
    order = models.PositiveIntegerField(default=0)
    release_offset_days = models.PositiveIntegerField(
        default=0,
        help_text="Days after a cohort's start date that this lesson unlocks.",
    )

    class Meta:
        db_table = "elearning_lessons"
        ordering = ["order", "created"]

    def __str__(self):
        return self.title


class Cohort(BaseModel):
    """A group receiving a course's lessons on a periodic (drip) schedule.

    Membership is reused from an existing Circle: the cohort's recipients are
    that circle's members. Lessons are released one per ``cadence_days`` from
    ``start_date``, in the course's module/lesson order.
    """

    name = models.CharField(max_length=255)
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="cohorts",
    )
    circle = models.ForeignKey(
        "children.Circle",
        on_delete=models.CASCADE,
        related_name="cohorts",
    )
    start_date = models.DateField()
    send_hour = models.PositiveSmallIntegerField(
        default=14,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text="Hour of day (0-23, Asia/Dili) at which due lessons are sent.",
    )
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elearning_cohorts"
        ordering = ["-created"]

    def __str__(self):
        return f"{self.name} ({self.course.title})"

    def recipients(self):
        return self.circle.members.all()

    def due_lessons(self, today):
        """Lessons whose release offset has been reached by ``today``.

        Pacing lives on each lesson (``release_offset_days``, counted from this
        cohort's ``start_date``). Returns them in delivery order.
        """
        if today < self.start_date:
            return self.course.ordered_lessons().none()
        elapsed = (today - self.start_date).days
        return self.course.ordered_lessons().filter(
            release_offset_days__lte=elapsed
        )


class LessonRelease(BaseModel):
    """Records that a cohort has been released a lesson (drip progress)."""

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="releases",
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="releases",
    )
    released_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elearning_lesson_releases"
        ordering = ["released_at"]
        unique_together = [("cohort", "lesson")]

    def __str__(self):
        return f"{self.cohort.name} -> {self.lesson.title}"


class LessonCompletion(BaseModel):
    """A recipient marking a released lesson as watched (via WhatsApp button)."""

    release = models.ForeignKey(
        LessonRelease,
        on_delete=models.CASCADE,
        related_name="completions",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_completions",
    )

    class Meta:
        db_table = "elearning_lesson_completions"
        ordering = ["created"]
        unique_together = [("release", "user")]

    def __str__(self):
        return f"{self.user} watched {self.release.lesson.title}"
