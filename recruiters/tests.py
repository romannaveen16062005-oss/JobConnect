from django.test import TestCase
from django.contrib.auth import get_user_model

from .models import Company, RecruiterProfile

User = get_user_model()


class CompanyModelTests(TestCase):

    def test_create_company(self):
        company = Company.objects.create(
            name="Tech Solutions",
            website="https://example.com",
            industry="Information Technology",
            location="Coimbatore"
        )

        self.assertEqual(company.name, "Tech Solutions")
        self.assertEqual(str(company), "Tech Solutions")

    def test_company_optional_fields(self):
        company = Company.objects.create(name="Startup Company")

        self.assertEqual(company.website, "")
        self.assertEqual(company.industry, "")
        self.assertEqual(company.location, "")


class RecruiterProfileModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="recruiter@example.com",
            password="TestPass123!",
            role="RECRUITER"
        )

        self.company = Company.objects.create(
            name="Tech Solutions"
        )

    def test_create_recruiter_profile(self):
        profile = RecruiterProfile.objects.create(
            user=self.user,
            company=self.company,
            designation="HR Manager",
            phone="9876543210"
        )

        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.company, self.company)
        self.assertEqual(profile.designation, "HR Manager")

    def test_recruiter_profile_without_company(self):
        profile = RecruiterProfile.objects.create(
            user=self.user
        )

        self.assertIsNone(profile.company)

    def test_recruiter_profile_string(self):
        profile = RecruiterProfile.objects.create(
            user=self.user
        )

        self.assertEqual(
            str(profile),
            "recruiter@example.com - Recruiter"
        )

    def test_company_deletion_sets_company_null(self):
        profile = RecruiterProfile.objects.create(
            user=self.user,
            company=self.company
        )

        self.company.delete()
        profile.refresh_from_db()

        self.assertIsNone(profile.company)

    def test_user_deletion_deletes_recruiter_profile(self):
        RecruiterProfile.objects.create(
            user=self.user,
            company=self.company
        )

        self.user.delete()

        self.assertFalse(
            RecruiterProfile.objects.filter(
                user_id=self.user.id
            ).exists()
        )