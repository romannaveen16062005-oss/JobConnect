
from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User
from recruiters.models import Company, RecruiterProfile
from jobs.models import Job
from jobseekers.models import JobSeekerProfile, Resume
from applications.models import Application, ApplicationStatusHistory


class AutomaticResumeAttachmentTests(TestCase):

    def setUp(self):
        # Create Job Seeker
        self.seeker = User.objects.create_user(
            email="seeker@test.com",
            password="TestPass123!",
            role=User.Role.SEEKER
        )

        self.profile = JobSeekerProfile.objects.create(
            user=self.seeker
        )

        # Create Recruiter
        self.recruiter_user = User.objects.create_user(
            email="recruiter@test.com",
            password="TestPass123!",
            role=User.Role.RECRUITER
        )

        self.company = Company.objects.create(
            name="Test Company"
        )

        self.recruiter_profile = RecruiterProfile.objects.create(
            user=self.recruiter_user,
            company=self.company
        )

        # Create approved job
        self.job = Job.objects.create(
            recruiter=self.recruiter_profile,
            title="Python Developer",
            description="Python development role",
            requirements="Python and Django",
            responsibilities="Develop applications",
            location="Coimbatore",
            approval_status=Job.ApprovalStatus.APPROVED,
            is_active=True
        )

        self.apply_url = reverse(
            "apply_job",
            args=[self.job.id]
        )

    def create_resume(self, title, is_default):
        uploaded_file = SimpleUploadedFile(
            f"{title.replace(' ', '_')}.pdf",
            b"%PDF-1.4 test resume content",
            content_type="application/pdf"
        )

        return Resume.objects.create(
            profile=self.profile,
            title=title,
            file=uploaded_file,
            is_default=is_default
        )

    def test_default_resume_is_automatically_attached(self):
        resume = self.create_resume(
            "Default Resume",
            True
        )

        self.client.force_login(self.seeker)

        response = self.client.post(self.apply_url)

        self.assertEqual(response.status_code, 302)

        application = Application.objects.get(
            applicant=self.seeker,
            job=self.job
        )

        self.assertEqual(application.resume, resume)

    def test_application_is_created_without_resume(self):
        self.client.force_login(self.seeker)

        response = self.client.post(self.apply_url)

        self.assertEqual(response.status_code, 302)

        application = Application.objects.get(
            applicant=self.seeker,
            job=self.job
        )

        self.assertIsNone(application.resume)

    def test_non_default_resume_is_not_attached(self):
        self.create_resume(
            "Other Resume",
            False
        )

        self.client.force_login(self.seeker)

        self.client.post(self.apply_url)

        application = Application.objects.get(
            applicant=self.seeker,
            job=self.job
        )

        self.assertIsNone(application.resume)

    def test_duplicate_application_is_prevented(self):
        resume = self.create_resume(
            "Default Resume",
            True
        )

        self.client.force_login(self.seeker)

        self.client.post(self.apply_url)
        self.client.post(self.apply_url)

        self.assertEqual(
            Application.objects.filter(
                applicant=self.seeker,
                job=self.job
            ).count(),
            1
        )

        application = Application.objects.get(
            applicant=self.seeker,
            job=self.job
        )

        self.assertEqual(application.resume, resume)

    def test_application_status_history_is_created_once(self):
        self.client.force_login(self.seeker)

        self.client.post(self.apply_url)
        self.client.post(self.apply_url)

        application = Application.objects.get(
            applicant=self.seeker,
            job=self.job
        )

        self.assertEqual(
            ApplicationStatusHistory.objects.filter(
                application=application
            ).count(),
            1
        )

        history = ApplicationStatusHistory.objects.get(
            application=application
        )

        self.assertEqual(
            history.new_status,
            Application.Status.APPLIED
        )
