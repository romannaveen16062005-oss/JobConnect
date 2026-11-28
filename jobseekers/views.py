
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import ResumeUploadForm
from .models import JobSeekerProfile


@login_required
def upload_resume(request):
    if request.user.role != "SEEKER":
        messages.error(request, "Only Job Seekers can upload resumes.")
        return redirect("job_list")

    profile, _ = JobSeekerProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":
        form = ResumeUploadForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                profile.resumes.filter(is_default=True).update(
                    is_default=False
                )

                resume = form.save(commit=False)
                resume.profile = profile
                resume.is_default = True
                resume.save()

            messages.success(
                request,
                "Resume uploaded successfully and set as default."
            )
            return redirect("upload_resume")

        messages.error(request, "Please correct the errors below.")

    else:
        form = ResumeUploadForm()

    resumes = profile.resumes.order_by("-uploaded_at")

    return render(request, "jobseekers/upload_resume.html", {
        "form": form,
        "resumes": resumes,
    })
