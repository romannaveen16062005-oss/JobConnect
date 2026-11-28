from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from recruiters.models import RecruiterProfile
from .forms import JobForm
from .models import Job


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
def recruiter_dashboard(request):
    jobs = Job.objects.filter(
        recruiter=request.recruiter_profile
    ).order_by("-created_at")

    return render(request, "jobs/recruiter_dashboard.html", {
        "jobs": jobs,
    })


@recruiter_required
def create_job(request):
    if request.method == "POST":
        form = JobForm(request.POST)

        if form.is_valid():
            job = form.save(commit=False)
            job.recruiter = request.recruiter_profile
            job.approval_status = Job.ApprovalStatus.PENDING
            job.is_active = True
            job.save()

            messages.success(
                request,
                "Job submitted successfully. Waiting for admin approval."
            )
            return redirect("recruiter_dashboard")
    else:
        form = JobForm()

    return render(request, "jobs/job_form.html", {
        "form": form,
        "page_title": "Create Job",
    })


@recruiter_required
def edit_job(request, job_id):
    job = get_object_or_404(
        Job,
        id=job_id,
        recruiter=request.recruiter_profile
    )

    if request.method == "POST":
        form = JobForm(request.POST, instance=job)

        if form.is_valid():
            updated_job = form.save(commit=False)
            updated_job.approval_status = Job.ApprovalStatus.PENDING
            updated_job.save()

            messages.success(
                request,
                "Job updated. It is waiting for admin approval again."
            )
            return redirect("recruiter_dashboard")
    else:
        form = JobForm(instance=job)

    return render(request, "jobs/job_form.html", {
        "form": form,
        "page_title": "Edit Job",
    })


@recruiter_required
@require_POST
def delete_job(request, job_id):
    job = get_object_or_404(
        Job,
        id=job_id,
        recruiter=request.recruiter_profile
    )

    job.delete()
    messages.success(request, "Job deleted successfully.")

    return redirect("recruiter_dashboard")