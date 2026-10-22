from rest_framework import serializers

from .models import Cohort, Course, CourseRun, Lesson, LessonRelease, Module


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id", "module", "title", "description", "youtube_url",
            "order", "release_offset_days",
        ]
        read_only_fields = ["id"]


class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = ["id", "course", "title", "order", "lessons"]
        read_only_fields = ["id"]


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)
    lesson_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "title", "description", "modules", "lesson_count", "created"]
        read_only_fields = ["id", "created"]

    def get_lesson_count(self, obj):
        return obj.ordered_lessons().count()


class CourseRunSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    released_count = serializers.SerializerMethodField()
    total_lessons = serializers.SerializerMethodField()

    class Meta:
        model = CourseRun
        fields = [
            "id", "cohort", "course", "course_title", "start_date",
            "send_hour", "active", "released_count", "total_lessons", "created",
        ]
        read_only_fields = ["id", "created"]

    def get_released_count(self, obj):
        return obj.releases.count()

    def get_total_lessons(self, obj):
        return obj.course.ordered_lessons().count()


class CohortSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    active_run = serializers.SerializerMethodField()

    class Meta:
        model = Cohort
        fields = ["id", "name", "member_count", "active_run", "created"]
        read_only_fields = ["id", "created"]

    def get_member_count(self, obj):
        return obj.members.count()

    def get_active_run(self, obj):
        # Filter in Python so a prefetched runs__course is reused (no query
        # per cohort).
        run = next((r for r in obj.runs.all() if r.active), None)
        return CourseRunSerializer(run).data if run else None


class LessonReleaseSerializer(serializers.ModelSerializer):
    lesson_title = serializers.CharField(source="lesson.title", read_only=True)
    youtube_url = serializers.CharField(source="lesson.youtube_url", read_only=True)
    completion_count = serializers.SerializerMethodField()

    class Meta:
        model = LessonRelease
        fields = [
            "id", "lesson", "lesson_title", "youtube_url",
            "completion_count", "released_at",
        ]
        read_only_fields = ["id", "released_at"]

    def get_completion_count(self, obj):
        return obj.completions.count()
