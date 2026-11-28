from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from jobs.models import Job
from applications.models import Application, ApplicationStatusHistory
from jobseekers.models import JobSeekerProfile
def job_list(request):
    jobs = Job.objects.filter(
        approval_status=Job.ApprovalStatus.APPROVED,
        is_active=True
    ).select_related("recruiter__company")
    keyword = request.GET.get("q", "").strip()
    location = request.GET.get("location", "").strip()
    job_type = request.GET.get("job_type", "").strip()
    if keyword:
        jobs = jobs.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(requirements__icontains=keyword)
            | Q(recruiter__company__name__icontains=keyword)
        )
    if location:
        jobs = jobs.filter(location__icontains=location)
    if job_type:
        jobs = jobs.filter(job_type=job_type)
    return render(request, "core/job_list.html", {
        "jobs": jobs,
        "keyword": keyword,
        "location": location,
        "selected_job_type": job_type,
        "job_types": Job.JobType.choices,
    })
def job_detail(request, job_id):
    job = get_object_or_404(
        Job.objects.select_related("recruiter__company"),
        id=job_id,
        approval_status=Job.ApprovalStatus.APPROVED,
        is_active=True
    )
    has_applied = False
    if request.user.is_authenticated and request.user.role == "SEEKER":
        has_applied = Application.objects.filter(
            applicant=request.user,
            job=job
        ).exists()
    return render(request, "core/job_detail.html", {
        "job": job,
        "has_applied": has_applied,
    })
@login_required
@require_POST
def apply_job(request, job_id):
    job = get_object_or_404(
        Job,
        id=job_id,
        approval_status=Job.ApprovalStatus.APPROVED,
        is_active=True
    )

    if request.user.role != "SEEKER":
        messages.error(request, "Only Job Seekers can apply for jobs.")
        return redirect("job_detail", job_id=job.id)

    profile = JobSeekerProfile.objects.filter(
        user=request.user
    ).first()

    default_resume = None
    if profile:
        default_resume = profile.resumes.filter(
            is_default=True
        ).first()

    application, created = Application.objects.get_or_create(
        applicant=request.user,
        job=job,
        defaults={"resume": default_resume}
    )

    if created:
        ApplicationStatusHistory.objects.create(
            application=application,
            old_status="",
            new_status=Application.Status.APPLIED,
            changed_by=request.user,
            note="Application submitted."
        )
        messages.success(
            request,
            "Your application was submitted successfully."
        )
    else:
        messages.info(request, "You have already applied for this job.")

    return redirect("job_detail", job_id=job.id)

@login_required
def my_applications(request):
    if request.user.role != "SEEKER":
        messages.error(request, "Only Job Seekers can view applications.")
        return redirect("job_list")
    applications = Application.objects.filter(
        applicant=request.user
    ).select_related(
        "job",
        "job__recruiter__company"
    )
    return render(
        request,
        "core/my_applications.html",
        {"applications": applications}
    )

@login_required
def my_profile(request):
    if request.user.role != "SEEKER":
        messages.error(request, "Only Job Seekers can access this profile.")
        return redirect("job_list")

    profile, created = JobSeekerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        request.user.first_name = request.POST.get("first_name", "").strip()
        request.user.last_name = request.POST.get("last_name", "").strip()
        request.user.save()

        profile.phone = request.POST.get("phone", "").strip()
        profile.location = request.POST.get("location", "").strip()
        profile.headline = request.POST.get("headline", "").strip()
        profile.summary = request.POST.get("summary", "").strip()
        profile.save()

        messages.success(request, "Your profile has been updated successfully.")
        return redirect("my_profile")

    return render(request, "core/my_profile.html", {
        "profile": profile
    })