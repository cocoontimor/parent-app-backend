from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from utils.models import BaseModel, SoftDeleteModel


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
        """All lessons in delivery order: by module order, then lesson order.

        Excludes soft-deleted lessons (via the default manager) and lessons
        under a soft-deleted module.
        """
        return Lesson.objects.filter(
            module__course=self, module__deleted__isnull=True
        ).order_by("module__order", "order")

    def lessons_with_release_day(self):
        """Each lesson in delivery order paired with its cumulative release day.

        ``release_offset_days`` is the gap *after the previous lesson*, so the
        release day is the running sum of offsets across modules and lessons in
        delivery order (the first lesson is offset from the run's start date).
        """
        day = 0
        result = []
        for lesson in self.ordered_lessons():
            day += lesson.release_offset_days
            result.append((lesson, day))
        return result


class Module(BaseModel, SoftDeleteModel):
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


class Lesson(BaseModel, SoftDeleteModel):
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
        help_text=(
            "Days after the previous lesson that this one unlocks (cumulative). "
            "The first lesson is counted from the cohort's start date; 0 means "
            "it releases together with the previous lesson."
        ),
    )

    class Meta:
        db_table = "elearning_lessons"
        ordering = ["order", "created"]

    def __str__(self):
        return self.title


class Cohort(BaseModel):
    """A named, reusable group of trainees.

    A cohort is just its people: ``members`` are the trainee users who receive
    lessons. Courses are run *for* a cohort via ``CourseRun`` records, so the
    same cohort can run one course now and another later without losing history.
    """

    name = models.CharField(max_length=255)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="cohorts",
        blank=True,
    )

    class Meta:
        db_table = "elearning_cohorts"
        ordering = ["-created"]

    def __str__(self):
        return self.name

    def recipients(self):
        return self.members.all()


class CourseRun(BaseModel):
    """A record of a cohort running a course from a start date (drip schedule).

    Owns the drip state: which course, when it started, the delivery hour, and
    (via ``releases``) which lessons have gone out. Changing the course or start
    date means opening a new run and leaving the old one as a record, so lesson
    releases and completions stay pinned to the run they happened in.
    """

    cohort = models.ForeignKey(
        Cohort,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    start_date = models.DateField()
    send_hour = models.PositiveSmallIntegerField(
        default=14,
        validators=[MinValueValidator(0), MaxValueValidator(23)],
        help_text="Hour of day (0-23, Asia/Dili) at which due lessons are sent.",
    )
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elearning_course_runs"
        ordering = ["-created"]

    def __str__(self):
        return f"{self.cohort.name} -> {self.course.title}"

    def recipients(self):
        return self.cohort.recipients()

    def due_lessons(self, today):
        """Lessons whose cumulative release day has been reached by ``today``.

        Pacing is cumulative: each lesson's ``release_offset_days`` counts from
        the previous lesson, so its release day is the running sum in delivery
        order (see ``Course.lessons_with_release_day``). Returns them in
        delivery order.
        """
        if today < self.start_date:
            return []
        elapsed = (today - self.start_date).days
        due = []
        for lesson, day in self.course.lessons_with_release_day():
            if day > elapsed:
                # Cumulative days are non-decreasing, so nothing later is due.
                break
            due.append(lesson)
        return due


class LessonRelease(BaseModel):
    """Records that a course run has released a lesson (drip progress)."""

    run = models.ForeignKey(
        CourseRun,
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
        unique_together = [("run", "lesson")]

    def __str__(self):
        return f"{self.run.cohort.name} -> {self.lesson.title}"


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
