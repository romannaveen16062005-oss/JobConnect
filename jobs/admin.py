from django.contrib import admin
from .models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "recruiter",
        "job_type",
        "experience_level",
        "approval_status",
        "is_active",
        "created_at",
    )

    list_filter = (
        "job_type",
        "experience_level",
        "approval_status",
        "is_active",
    )

    search_fields = (
        "title",
        "location",
        "recruiter__user__email",
    )

    readonly_fields = ("created_at", "updated_at")

    ordering = ("-created_at",)