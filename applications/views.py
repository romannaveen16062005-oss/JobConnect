
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from recruiters.models import RecruiterProfile
from .models import Application, ApplicationStatusHistory

from pathlib import Path
from django.http import FileResponse


def recruiter_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != "RECRUITER":
            messages.error(request, "Recruiter access required.")
            return redirect("job_list")

        try:
            request.recruiter_profile = request.user.recruiter_profile
        except RecruiterProfile.DoesNotExist:
            messages.error(request, "Recruiter profile not found.")
            return redirect("job_list")

        return view_func(request, *args, **kwargs)

    return wrapper


@recruiter_required
def applicant_list(request):
    applications = Application.objects.filter(
        job__recruiter=request.recruiter_profile
    ).select_related(
        "applicant",
        "job",
        "resume",
    ).order_by("-applied_at")

    status_choices = [
        choice for choice in Application.Status.choices
        if choice[0] not in (
            Application.Status.APPLIED,
            Application.Status.WITHDRAWN,
        )
    ]

    return render(request, "applications/applicant_list.html", {
        "applications": applications,
        "status_choices": status_choices,
    })


@recruiter_required
@require_POST
def update_application_status(request, application_id):
    application = get_object_or_404(
        Application,
        id=application_id,
        job__recruiter=request.recruiter_profile,
    )

    new_status = request.POST.get("status", "").strip()
    note = request.POST.get("note", "").strip()

    allowed_statuses = {
        Application.Status.UNDER_REVIEW,
        Application.Status.SHORTLISTED,
        Application.Status.INTERVIEW,
        Application.Status.SELECTED,
        Application.Status.REJECTED,
    }

    if new_status not in allowed_statuses:
        messages.error(request, "Invalid application status.")
        return redirect("applicant_list")

    if application.status == Application.Status.WITHDRAWN:
        messages.error(
            request,
            "Withdrawn applications cannot be updated."
        )
        return redirect("applicant_list")

    if application.status == new_status:
        messages.info(request, "Application already has this status.")
        return redirect("applicant_list")

    old_status = application.status

    with transaction.atomic():
        application.status = new_status
        application.save(update_fields=["status", "updated_at"])

        ApplicationStatusHistory.objects.create(
            application=application,
            old_status=old_status,
            new_status=new_status,
            changed_by=request.user,
            note=note,
        )

    messages.success(request, "Application status updated successfully.")
    return redirect("applicant_list")


@recruiter_required
def download_applicant_resume(request, application_id):
    application = get_object_or_404(
        Application.objects.select_related(
            "applicant",
            "resume",
            "resume__profile",
        ),
        id=application_id,
        job__recruiter=request.recruiter_profile,
    )

    resume = application.resume

    if not resume or resume.profile.user_id != application.applicant_id:
        messages.error(request, "Resume is not available.")
        return redirect("applicant_list")

    try:
        resume_file = resume.file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        messages.error(request, "Resume file could not be found.")
        return redirect("applicant_list")

    filename = Path(resume.file.name).name

    return FileResponse(
        resume_file,
        as_attachment=True,
        filename=filename,
        content_type="application/octet-stream",
    )
