
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from recruiters.models import Company, RecruiterProfile
from jobs.models import Job
from applications.models import (
    SavedJob,
    Application,
    ApplicationStatusHistory,
)

from django.core.files.uploadedfile import SimpleUploadedFile

from jobseekers.models import JobSeekerProfile, Resume

class ApplicationModuleTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seeker = User.objects.create_user(
            email="seeker@example.com",
            password="TestPass123",
            role=User.Role.SEEKER,
        )

        recruiter_user = User.objects.create_user(
            email="recruiter@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )

        company = Company.objects.create(
            name="TechNova Solutions"
        )

        recruiter = RecruiterProfile.objects.create(
            user=recruiter_user,
            company=company,
        )

        cls.job = Job.objects.create(
            recruiter=recruiter,
            title="Python Developer",
            description="Python development work.",
            requirements="Python and Django.",
            location="Coimbatore",
        )

    def test_save_job(self):
        saved_job = SavedJob.objects.create(
            user=self.seeker,
            job=self.job,
        )

        self.assertEqual(saved_job.user, self.seeker)
        self.assertEqual(saved_job.job, self.job)

    def test_duplicate_saved_job_rejected(self):
        SavedJob.objects.create(
            user=self.seeker,
            job=self.job,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedJob.objects.create(
                    user=self.seeker,
                    job=self.job,
                )

    def test_create_application(self):
        application = Application.objects.create(
            applicant=self.seeker,
            job=self.job,
        )

        self.assertEqual(
            application.status,
            Application.Status.APPLIED
        )
        self.assertEqual(application.applicant, self.seeker)
        self.assertEqual(application.job, self.job)

    def test_duplicate_application_rejected(self):
        Application.objects.create(
            applicant=self.seeker,
            job=self.job,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Application.objects.create(
                    applicant=self.seeker,
                    job=self.job,
                )

    def test_application_status_can_be_updated(self):
        application = Application.objects.create(
            applicant=self.seeker,
            job=self.job,
        )

        application.status = Application.Status.SHORTLISTED
        application.save()

        application.refresh_from_db()

        self.assertEqual(
            application.status,
            Application.Status.SHORTLISTED,
        )

    def test_application_status_history(self):
        application = Application.objects.create(
            applicant=self.seeker,
            job=self.job,
        )

        history = ApplicationStatusHistory.objects.create(
            application=application,
            old_status="",
            new_status=Application.Status.APPLIED,
            changed_by=self.seeker,
            note="Application submitted.",
        )

        self.assertEqual(history.application, application)
        self.assertEqual(
            history.new_status,
            Application.Status.APPLIED
        )

    def test_application_history_is_deleted_with_application(self):
        application = Application.objects.create(
            applicant=self.seeker,
            job=self.job,
        )

        ApplicationStatusHistory.objects.create(
            application=application,
            old_status="",
            new_status=Application.Status.APPLIED,
        )

        application.delete()

        self.assertEqual(
            ApplicationStatusHistory.objects.count(),
            0
        )


class RecruiterApplicantManagementTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.seeker = User.objects.create_user(
            email="applicant@example.com",
            password="TestPass123",
            role=User.Role.SEEKER,
            first_name="Arun",
            last_name="Kumar",
        )

        cls.recruiter_user = User.objects.create_user(
            email="recruiter@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )

        cls.other_recruiter_user = User.objects.create_user(
            email="other@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )

        company1 = Company.objects.create(
            name="TechNova Solutions"
        )

        company2 = Company.objects.create(
            name="Future Technologies"
        )

        cls.recruiter = RecruiterProfile.objects.create(
            user=cls.recruiter_user,
            company=company1,
        )

        cls.other_recruiter = RecruiterProfile.objects.create(
            user=cls.other_recruiter_user,
            company=company2,
        )

        cls.job = Job.objects.create(
            recruiter=cls.recruiter,
            title="Python Developer",
            description="Python development work.",
            requirements="Python and Django.",
            location="Coimbatore",
        )

        cls.other_job = Job.objects.create(
            recruiter=cls.other_recruiter,
            title="Java Developer",
            description="Java development work.",
            requirements="Java knowledge.",
            location="Chennai",
        )

    def setUp(self):
        self.client.force_login(self.recruiter_user)

        self.application = Application.objects.create(
            applicant=self.seeker,
            job=self.job,
        )

        self.other_application = Application.objects.create(
            applicant=self.seeker,
            job=self.other_job,
        )

    def test_recruiter_can_view_own_applicants(self):
        response = self.client.get(
            reverse("applicant_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Python Developer")
        self.assertContains(response, "applicant@example.com")
        self.assertNotContains(response, "Java Developer")

    def test_seeker_cannot_view_applicant_list(self):
        self.client.force_login(self.seeker)

        response = self.client.get(
            reverse("applicant_list")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    def test_anonymous_user_cannot_view_applicant_list(self):
        self.client.logout()

        response = self.client.get(
            reverse("applicant_list")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_recruiter_can_update_application_status(self):
        response = self.client.post(
            reverse(
                "update_application_status",
                args=[self.application.id]
            ),
            {
                "status": Application.Status.SHORTLISTED,
                "note": "Good candidate.",
            }
        )

        self.assertRedirects(
            response,
            reverse("applicant_list")
        )

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            Application.Status.SHORTLISTED
        )

        history = ApplicationStatusHistory.objects.get(
            application=self.application
        )

        self.assertEqual(
            history.old_status,
            Application.Status.APPLIED
        )
        self.assertEqual(
            history.new_status,
            Application.Status.SHORTLISTED
        )
        self.assertEqual(
            history.changed_by,
            self.recruiter_user
        )
        self.assertEqual(history.note, "Good candidate.")

    def test_invalid_application_status_is_rejected(self):
        response = self.client.post(
            reverse(
                "update_application_status",
                args=[self.application.id]
            ),
            {
                "status": "INVALID_STATUS",
                "note": "Invalid update",
            }
        )

        self.assertRedirects(
            response,
            reverse("applicant_list")
        )

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            Application.Status.APPLIED
        )
        self.assertEqual(
            ApplicationStatusHistory.objects.filter(
                application=self.application
            ).count(),
            0
        )


    def create_test_resume(self):
        profile, _ = JobSeekerProfile.objects.get_or_create(
            user=self.seeker
        )

        return Resume.objects.create(
            profile=profile,
            title="Applicant Resume",
            file=SimpleUploadedFile(
                "applicant.pdf",
                b"%PDF-1.4 Sample applicant resume",
                content_type="application/pdf",
            ),
            is_default=True,
        )

    def test_recruiter_can_download_own_applicants_resume(self):
        resume = self.create_test_resume()
        self.application.resume = resume
        self.application.save()

        response = self.client.get(
            reverse(
                "download_applicant_resume",
                args=[self.application.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "attachment",
            response["Content-Disposition"],
        )
        self.assertTrue(
            response["Content-Disposition"].endswith(".pdf\"")
        )

        response.close()

    def test_other_recruiter_cannot_download_resume(self):
        resume = self.create_test_resume()
        self.other_application.resume = resume
        self.other_application.save()

        response = self.client.get(
            reverse(
                "download_applicant_resume",
                args=[self.other_application.id],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_seeker_cannot_download_applicant_resume(self):
        resume = self.create_test_resume()
        self.application.resume = resume
        self.application.save()

        self.client.force_login(self.seeker)

        response = self.client.get(
            reverse(
                "download_applicant_resume",
                args=[self.application.id],
            )
        )

        self.assertEqual(response.status_code, 302)

    def test_anonymous_user_cannot_download_resume(self):
        resume = self.create_test_resume()
        self.application.resume = resume
        self.application.save()

        self.client.logout()

        response = self.client.get(
            reverse(
                "download_applicant_resume",
                args=[self.application.id],
            )
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


    def test_recruiter_cannot_update_another_recruiters_application(self):
        response = self.client.post(
            reverse(
                "update_application_status",
                args=[self.other_application.id]
            ),
            {
                "status": Application.Status.SHORTLISTED,
            }
        )

        self.assertEqual(response.status_code, 404)

        self.other_application.refresh_from_db()

        self.assertEqual(
            self.other_application.status,
            Application.Status.APPLIED
        )

    def test_status_update_does_not_accept_get_request(self):
        response = self.client.get(
            reverse(
                "update_application_status",
                args=[self.application.id]
            )
        )

        self.assertEqual(response.status_code, 405)

    def test_withdrawn_application_cannot_be_updated(self):
        self.application.status = Application.Status.WITHDRAWN
        self.application.save()

        response = self.client.post(
            reverse(
                "update_application_status",
                args=[self.application.id]
            ),
            {
                "status": Application.Status.SHORTLISTED,
            }
        )

        self.assertRedirects(
            response,
            reverse("applicant_list")
        )

        self.application.refresh_from_db()

        self.assertEqual(
            self.application.status,
            Application.Status.WITHDRAWN
        )

    def test_same_status_does_not_create_duplicate_history(self):
        response = self.client.post(
            reverse(
                "update_application_status",
                args=[self.application.id]
            ),
            {
                "status": Application.Status.APPLIED,
            }
        )

        self.assertRedirects(
            response,
            reverse("applicant_list")
        )

        self.assertEqual(
            ApplicationStatusHistory.objects.filter(
                application=self.application
            ).count(),
            0
        )
