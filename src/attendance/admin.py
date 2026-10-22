from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ["child", "circle", "date", "status", "marked_by"]
    list_filter = ["status", "date", "circle"]
    search_fields = ["child__name"]
