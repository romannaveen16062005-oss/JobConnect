
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from recruiters.models import Company, RecruiterProfile
from jobs.models import Job


class JobModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="recruiter@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )
        cls.company = Company.objects.create(
            name="TechNova Solutions"
        )
        cls.recruiter = RecruiterProfile.objects.create(
            user=cls.user,
            company=cls.company,
            designation="HR Manager",
        )

    def create_job(self, **overrides):
        data = {
            "recruiter": self.recruiter,
            "title": "Python Developer",
            "description": "Develop Python applications.",
            "requirements": "Python and Django knowledge.",
            "location": "Coimbatore",
            "salary_min": Decimal("15000.00"),
            "salary_max": Decimal("25000.00"),
            "vacancies": 2,
        }
        data.update(overrides)
        return Job(**data)

    def test_valid_job_creation(self):
        job = self.create_job()
        job.full_clean()
        job.save()

        self.assertEqual(job.title, "Python Developer")
        self.assertEqual(
            job.approval_status,
            Job.ApprovalStatus.PENDING
        )

    def test_maximum_salary_cannot_be_less_than_minimum(self):
        job = self.create_job(
            salary_min=Decimal("30000.00"),
            salary_max=Decimal("20000.00"),
        )

        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_negative_minimum_salary_is_rejected(self):
        job = self.create_job(
            salary_min=Decimal("-1000.00")
        )

        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_negative_maximum_salary_is_rejected(self):
        job = self.create_job(
            salary_max=Decimal("-1000.00")
        )

        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_zero_vacancies_is_rejected(self):
        job = self.create_job(vacancies=0)

        with self.assertRaises(ValidationError):
            job.full_clean()

    def test_optional_salary_is_allowed(self):
        job = self.create_job(
            salary_min=None,
            salary_max=None
        )
        job.full_clean()
        job.save()

        self.assertIsNone(job.salary_min)
        self.assertIsNone(job.salary_max)

    def test_database_rejects_invalid_salary_range(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_job(
                    salary_min=Decimal("30000.00"),
                    salary_max=Decimal("20000.00"),
                ).save()

    def test_database_rejects_zero_vacancies(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self.create_job(vacancies=0).save()


class RecruiterJobManagementTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.company1 = Company.objects.create(
            name="TechNova Solutions"
        )
        cls.company2 = Company.objects.create(
            name="Future Technologies"
        )

        cls.recruiter_user = User.objects.create_user(
            email="recruiter1@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )

        cls.other_recruiter_user = User.objects.create_user(
            email="recruiter2@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )

        cls.seeker_user = User.objects.create_user(
            email="seeker@example.com",
            password="TestPass123",
            role=User.Role.SEEKER,
        )

        cls.recruiter = RecruiterProfile.objects.create(
            user=cls.recruiter_user,
            company=cls.company1,
        )

        cls.other_recruiter = RecruiterProfile.objects.create(
            user=cls.other_recruiter_user,
            company=cls.company2,
        )

    def setUp(self):
        self.client.force_login(self.recruiter_user)

    def create_job(self, recruiter=None, **overrides):
        data = {
            "recruiter": recruiter or self.recruiter,
            "title": "Python Developer",
            "description": "Develop Python applications.",
            "requirements": "Python and Django knowledge.",
            "location": "Coimbatore",
            "job_type": Job.JobType.FULL_TIME,
            "experience_level": Job.ExperienceLevel.FRESHER,
            "salary_min": Decimal("15000.00"),
            "salary_max": Decimal("25000.00"),
            "vacancies": 2,
        }
        data.update(overrides)
        return Job.objects.create(**data)

    def valid_job_data(self, **overrides):
        data = {
            "title": "Python Developer",
            "description": "Develop Python applications.",
            "requirements": "Python and Django knowledge.",
            "responsibilities": "Build and maintain applications.",
            "location": "Coimbatore",
            "job_type": Job.JobType.FULL_TIME,
            "experience_level": Job.ExperienceLevel.FRESHER,
            "salary_min": "15000",
            "salary_max": "25000",
            "vacancies": "2",
        }
        data.update(overrides)
        return data

    def test_recruiter_dashboard_shows_only_own_jobs(self):
        own_job = self.create_job()
        other_job = self.create_job(
            recruiter=self.other_recruiter,
            title="Java Developer",
        )

        response = self.client.get(
            reverse("recruiter_dashboard")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, own_job.title)
        self.assertNotContains(response, other_job.title)

    def test_job_seeker_cannot_access_recruiter_dashboard(self):
        self.client.force_login(self.seeker_user)

        response = self.client.get(
            reverse("recruiter_dashboard")
        )

        self.assertRedirects(
            response,
            reverse("job_list")
        )

    def test_anonymous_user_cannot_access_recruiter_dashboard(self):
        self.client.logout()

        response = self.client.get(
            reverse("recruiter_dashboard")
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("login"),
            response.url
        )

    def test_recruiter_can_create_job_with_pending_status(self):
        response = self.client.post(
            reverse("create_job"),
            self.valid_job_data()
        )

        self.assertRedirects(
            response,
            reverse("recruiter_dashboard")
        )

        job = Job.objects.get(title="Python Developer")

        self.assertEqual(job.recruiter, self.recruiter)
        self.assertEqual(
            job.approval_status,
            Job.ApprovalStatus.PENDING
        )
        self.assertTrue(job.is_active)

    def test_recruiter_can_edit_own_job(self):
        job = self.create_job(
            approval_status=Job.ApprovalStatus.APPROVED
        )

        response = self.client.post(
            reverse("edit_job", args=[job.id]),
            self.valid_job_data(
                title="Senior Python Developer"
            )
        )

        self.assertRedirects(
            response,
            reverse("recruiter_dashboard")
        )

        job.refresh_from_db()

        self.assertEqual(
            job.title,
            "Senior Python Developer"
        )
        self.assertEqual(
            job.approval_status,
            Job.ApprovalStatus.PENDING
        )

    def test_recruiter_cannot_edit_another_recruiters_job(self):
        job = self.create_job(
            recruiter=self.other_recruiter
        )

        response = self.client.get(
            reverse("edit_job", args=[job.id])
        )

        self.assertEqual(response.status_code, 404)

    def test_recruiter_can_delete_own_job(self):
        job = self.create_job()

        response = self.client.post(
            reverse("delete_job", args=[job.id])
        )

        self.assertRedirects(
            response,
            reverse("recruiter_dashboard")
        )

        self.assertFalse(
            Job.objects.filter(id=job.id).exists()
        )

    def test_recruiter_cannot_delete_another_recruiters_job(self):
        job = self.create_job(
            recruiter=self.other_recruiter
        )

        response = self.client.post(
            reverse("delete_job", args=[job.id])
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(
            Job.objects.filter(id=job.id).exists()
        )

    def test_job_delete_does_not_accept_get_request(self):
        job = self.create_job()

        response = self.client.get(
            reverse("delete_job", args=[job.id])
        )

        self.assertEqual(response.status_code, 405)
        self.assertTrue(
            Job.objects.filter(id=job.id).exists()
        )
