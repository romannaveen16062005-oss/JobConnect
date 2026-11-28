
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from accounts.models import User
from applications.models import Application, ApplicationStatusHistory
from jobseekers.models import JobSeekerProfile
from jobs.models import Job


def admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if (
            request.user.role != User.Role.ADMIN
            or not request.user.is_staff
        ):
            messages.error(request, "Admin access required.")
            return redirect("job_list")

        return view_func(request, *args, **kwargs)

    return wrapper


@admin_required
def admin_dashboard(request):
    context = {
        "total_users": User.objects.count(),
        "total_seekers": User.objects.filter(
            role=User.Role.SEEKER
        ).count(),
        "total_recruiters": User.objects.filter(
            role=User.Role.RECRUITER
        ).count(),
        "total_jobs": Job.objects.count(),
        "pending_jobs": Job.objects.filter(
            approval_status=Job.ApprovalStatus.PENDING
        ).count(),
        "approved_jobs": Job.objects.filter(
            approval_status=Job.ApprovalStatus.APPROVED
        ).count(),
        "rejected_jobs": Job.objects.filter(
            approval_status=Job.ApprovalStatus.REJECTED
        ).count(),
        "total_applications": Application.objects.count(),
        "application_stats": Application.objects.values(
            "status"
        ).annotate(
            total=Count("id")
        ).order_by("status"),
        "recent_jobs": Job.objects.select_related(
            "recruiter__company"
        ).order_by("-created_at")[:5],
    }

    return render(
        request,
        "core/admin_dashboard.html",
        context
    )


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
        messages.error(
            request,
            "Only Job Seekers can apply for jobs."
        )
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
        messages.info(
            request,
            "You have already applied for this job."
        )

    return redirect("job_detail", job_id=job.id)


@login_required
def my_applications(request):
    if request.user.role != "SEEKER":
        messages.error(
            request,
            "Only Job Seekers can view applications."
        )
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
        messages.error(
            request,
            "Only Job Seekers can access this profile."
        )
        return redirect("job_list")

    profile, created = JobSeekerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        request.user.first_name = request.POST.get(
            "first_name", ""
        ).strip()

        request.user.last_name = request.POST.get(
            "last_name", ""
        ).strip()

        request.user.save()

        profile.phone = request.POST.get("phone", "").strip()
        profile.location = request.POST.get("location", "").strip()
        profile.headline = request.POST.get("headline", "").strip()
        profile.summary = request.POST.get("summary", "").strip()
        profile.save()

        messages.success(
            request,
            "Your profile has been updated successfully."
        )

        return redirect("my_profile")

    return render(request, "core/my_profile.html", {
        "profile": profile
    })


@admin_required
def admin_pending_jobs(request):
    pending_jobs = Job.objects.filter(
        approval_status=Job.ApprovalStatus.PENDING
    ).select_related(
        "recruiter__company",
        "recruiter__user"
    ).order_by("-created_at")

    return render(request, "core/admin_pending_jobs.html", {
        "pending_jobs": pending_jobs,
    })


@admin_required
@require_POST
def admin_job_action(request, job_id, action):
    job = get_object_or_404(
        Job,
        id=job_id,
        approval_status=Job.ApprovalStatus.PENDING
    )

    if action == "approve":
        job.approval_status = Job.ApprovalStatus.APPROVED
        job.is_active = True
        message = "Job approved successfully."

    elif action == "reject":
        job.approval_status = Job.ApprovalStatus.REJECTED
        job.is_active = False
        message = "Job rejected successfully."

    else:
        messages.error(request, "Invalid job action.")
        return redirect("admin_pending_jobs")

    job.save(update_fields=[
        "approval_status",
        "is_active",
        "updated_at"
    ])

    messages.success(request, message)

    return redirect("admin_pending_jobs")


@admin_required
def admin_users(request):
    users = User.objects.all().order_by("-date_joined")

    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()
    keyword = request.GET.get("q", "").strip()

    valid_roles = [
        choice[0] for choice in User.Role.choices
    ]

    if role in valid_roles:
        users = users.filter(role=role)

    if status == "active":
        users = users.filter(is_active=True)

    elif status == "inactive":
        users = users.filter(is_active=False)

    if keyword:
        users = users.filter(
            Q(email__icontains=keyword)
            | Q(first_name__icontains=keyword)
            | Q(last_name__icontains=keyword)
        )

    paginator = Paginator(users, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "core/admin_users.html", {
        "page_obj": page_obj,
        "selected_role": role,
        "selected_status": status,
        "keyword": keyword,
        "roles": User.Role.choices,
    })
