
from django.contrib import admin
from .models import (
    SavedJob,
    Application,
    ApplicationStatusHistory,
)


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display = ("user", "job", "saved_at")
    search_fields = ("user__email", "job__title")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "applicant",
        "job",
        "status",
        "applied_at",
    )
    list_filter = ("status", "applied_at")
    search_fields = ("applicant__email", "job__title")
    readonly_fields = ("applied_at", "updated_at")


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "old_status",
        "new_status",
        "changed_by",
        "changed_at",
    )
    list_filter = ("new_status", "changed_at")
