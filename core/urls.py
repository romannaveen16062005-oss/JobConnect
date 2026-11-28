from django.urls import path
from . import views

urlpatterns = [
    # Admin Dashboard
    path(
        "admin-dashboard/",
        views.admin_dashboard,
        name="admin_dashboard"
    ),
    path(
        "admin-dashboard/pending-jobs/",
        views.admin_pending_jobs,
        name="admin_pending_jobs"
    ),
    path(
        "admin-dashboard/jobs/<int:job_id>/<str:action>/",
        views.admin_job_action,
        name="admin_job_action"
    ),

    # Public Jobs
    path("", views.job_list, name="job_list"),
    path("jobs/<int:job_id>/", views.job_detail, name="job_detail"),
    path("jobs/<int:job_id>/apply/", views.apply_job, name="apply_job"),

    # Job Seeker
    path("my-applications/", views.my_applications, name="my_applications"),
    path("my-profile/", views.my_profile, name="my_profile"),

    path(
        "admin-dashboard/users/",
        views.admin_users,
        name="admin_users"
    ),
]
