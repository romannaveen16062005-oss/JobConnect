
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("recruiter/jobs/", include("jobs.urls")),
    path("recruiter/", include("applications.urls")),
    path("profile/resumes/", include("jobseekers.urls")),
    path("", include("core.urls")),
]
