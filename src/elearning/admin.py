from django.contrib import admin

from .models import (
    Cohort,
    Course,
    Lesson,
    LessonCompletion,
    LessonRelease,
    Module,
)


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 0


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "created"]
    inlines = [ModuleInline]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["title", "course", "order"]
    list_filter = ["course"]
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ["title", "module", "order", "release_offset_days", "youtube_url"]
    list_filter = ["module__course"]


@admin.register(Cohort)
class CohortAdmin(admin.ModelAdmin):
    list_display = ["name", "course", "circle", "start_date", "send_hour", "active"]
    list_filter = ["active", "course"]


@admin.register(LessonRelease)
class LessonReleaseAdmin(admin.ModelAdmin):
    list_display = ["cohort", "lesson", "released_at"]
    list_filter = ["cohort"]


@admin.register(LessonCompletion)
class LessonCompletionAdmin(admin.ModelAdmin):
    list_display = ["user", "release", "created"]
    list_filter = ["release__cohort"]
