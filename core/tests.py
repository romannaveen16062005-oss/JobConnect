
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
        self.seeker = User.objects.create_user(
            email="seeker@test.com",
            password="TestPass123!",
            role=User.Role.SEEKER
        )

        self.profile = JobSeekerProfile.objects.create(
            user=self.seeker
        )

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


class AdminDashboardTests(TestCase):

    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="TestPass123!",
            role=User.Role.ADMIN,
            is_staff=True
        )

        self.seeker = User.objects.create_user(
            email="seeker_admin_test@test.com",
            password="TestPass123!",
            role=User.Role.SEEKER
        )

        self.recruiter_user = User.objects.create_user(
            email="recruiter_admin_test@test.com",
            password="TestPass123!",
            role=User.Role.RECRUITER
        )

        self.company = Company.objects.create(
            name="Admin Test Company"
        )

        self.recruiter = RecruiterProfile.objects.create(
            user=self.recruiter_user,
            company=self.company
        )

        self.pending_job = Job.objects.create(
            recruiter=self.recruiter,
            title="Pending Python Developer",
            description="Python development",
            requirements="Python and Django",
            responsibilities="Build applications",
            location="Coimbatore",
            approval_status=Job.ApprovalStatus.PENDING
        )

        self.approved_job = Job.objects.create(
            recruiter=self.recruiter,
            title="Approved Developer",
            description="Development role",
            requirements="Python",
            responsibilities="Development",
            location="Coimbatore",
            approval_status=Job.ApprovalStatus.APPROVED
        )

    # USER MANAGEMENT TESTS

    def test_admin_can_access_user_management(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_users")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "core/admin_users.html"
        )

    def test_seeker_cannot_access_user_management(self):
        self.client.force_login(self.seeker)

        response = self.client.get(
            reverse("admin_users")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    def test_recruiter_cannot_access_user_management(self):
        self.client.force_login(self.recruiter_user)

        response = self.client.get(
            reverse("admin_users")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    def test_user_management_role_filter(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_users"),
            {"role": "SEEKER"}
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            list(response.context["page_obj"].object_list),
            [self.seeker]
        )

    def test_user_management_search(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_users"),
            {"q": "recruiter_admin_test"}
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            list(response.context["page_obj"].object_list),
            [self.recruiter_user]
        )

    def test_user_management_active_inactive_filter(self):
        inactive_user = User.objects.create_user(
            email="inactive_user@test.com",
            password="TestPass123!",
            role=User.Role.SEEKER,
            is_active=False
        )

        self.client.force_login(self.admin)

        active_response = self.client.get(
            reverse("admin_users"),
            {"status": "active"}
        )

        inactive_response = self.client.get(
            reverse("admin_users"),
            {"status": "inactive"}
        )

        self.assertEqual(active_response.status_code, 200)
        self.assertEqual(inactive_response.status_code, 200)

        active_users = list(
            active_response.context["page_obj"].object_list
        )

        inactive_users = list(
            inactive_response.context["page_obj"].object_list
        )

        self.assertNotIn(inactive_user, active_users)
        self.assertIn(inactive_user, inactive_users)

    def test_user_management_pagination(self):
        for number in range(21):
            User.objects.create_user(
                email=f"pagination_user_{number}@test.com",
                password="TestPass123!",
                role=User.Role.SEEKER
            )

        self.client.force_login(self.admin)

        first_page = self.client.get(
            reverse("admin_users"),
            {"page": 1}
        )

        second_page = self.client.get(
            reverse("admin_users"),
            {"page": 2}
        )

        self.assertEqual(first_page.status_code, 200)
        self.assertEqual(second_page.status_code, 200)

        self.assertTrue(
            first_page.context["page_obj"].has_next()
        )

        self.assertEqual(
            first_page.context["page_obj"].number,
            1
        )

        self.assertEqual(
            second_page.context["page_obj"].number,
            2
        )

    # ADMIN DASHBOARD TESTS

    def test_admin_can_access_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertEqual(response.status_code, 200)

        self.assertTemplateUsed(
            response,
            "core/admin_dashboard.html"
        )

        self.assertEqual(
            response.context["total_jobs"],
            2
        )

    def test_job_seeker_cannot_access_dashboard(self):
        self.client.force_login(self.seeker)

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    def test_recruiter_cannot_access_dashboard(self):
        self.client.force_login(self.recruiter_user)

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    def test_admin_without_staff_permission_is_denied(self):
        non_staff_admin = User.objects.create_user(
            email="nonstaff@test.com",
            password="TestPass123!",
            role=User.Role.ADMIN,
            is_staff=False
        )

        self.client.force_login(non_staff_admin)

        response = self.client.get(
            reverse("admin_dashboard")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    # JOB APPROVAL TESTS

    def test_pending_jobs_page_shows_only_pending_jobs(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse("admin_pending_jobs")
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            list(response.context["pending_jobs"]),
            [self.pending_job]
        )

    def test_admin_can_approve_pending_job(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "admin_job_action",
                args=[self.pending_job.id, "approve"]
            )
        )

        self.assertRedirects(
            response,
            reverse("admin_pending_jobs")
        )

        self.pending_job.refresh_from_db()

        self.assertEqual(
            self.pending_job.approval_status,
            Job.ApprovalStatus.APPROVED
        )

        self.assertTrue(self.pending_job.is_active)

    def test_admin_can_reject_pending_job(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse(
                "admin_job_action",
                args=[self.pending_job.id, "reject"]
            )
        )

        self.assertRedirects(
            response,
            reverse("admin_pending_jobs")
        )

        self.pending_job.refresh_from_db()

        self.assertEqual(
            self.pending_job.approval_status,
            Job.ApprovalStatus.REJECTED
        )

        self.assertFalse(self.pending_job.is_active)

    def test_get_request_cannot_approve_job(self):
        self.client.force_login(self.admin)

        response = self.client.get(
            reverse(
                "admin_job_action",
                args=[self.pending_job.id, "approve"]
            )
        )

        self.assertEqual(response.status_code, 405)

        self.pending_job.refresh_from_db()

        self.assertEqual(
            self.pending_job.approval_status,
            Job.ApprovalStatus.PENDING
        )

    def test_recruiter_cannot_approve_own_job(self):
        self.client.force_login(self.recruiter_user)

        response = self.client.post(
            reverse(
                "admin_job_action",
                args=[self.pending_job.id, "approve"]
            )
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

        self.pending_job.refresh_from_db()

        self.assertEqual(
            self.pending_job.approval_status,
            Job.ApprovalStatus.PENDING
        )
