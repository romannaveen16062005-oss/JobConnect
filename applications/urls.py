
from django.urls import path

from . import views

urlpatterns = [
    path(
        "applicants/",
        views.applicant_list,
        name="applicant_list"
    ),
    path(
        "applicants/<int:application_id>/status/",
        views.update_application_status,
        name="update_application_status"
    ),
    path(
    "applicants/<int:application_id>/resume/",
    views.download_applicant_resume,
    name="download_applicant_resume"
    ),
]
