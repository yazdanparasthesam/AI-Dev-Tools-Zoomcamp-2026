from django.contrib import admin

from .models import Chore, Completion, Member


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "is_active", "points", "completion_count", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "email")


@admin.register(Chore)
class ChoreAdmin(admin.ModelAdmin):
    list_display = ("name", "recurrence", "assigned_to", "difficulty", "due_date", "status", "is_active")
    list_filter = ("recurrence", "is_active", "assignment_mode", "assigned_to")
    search_fields = ("name", "description")
    date_hierarchy = "due_date"


@admin.register(Completion)
class CompletionAdmin(admin.ModelAdmin):
    list_display = ("chore", "completed_by", "completed_at", "points_awarded", "was_late")
    list_filter = ("was_late", "completed_by")
    search_fields = ("chore__name", "note")
    date_hierarchy = "completed_at"
