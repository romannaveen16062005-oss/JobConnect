from django.urls import path

from . import views

urlpatterns = [
    path("", views.recruiter_dashboard, name="recruiter_dashboard"),
    path("create/", views.create_job, name="create_job"),
    path("<int:job_id>/edit/", views.edit_job, name="edit_job"),
    path("<int:job_id>/delete/", views.delete_job, name="delete_job"),
]