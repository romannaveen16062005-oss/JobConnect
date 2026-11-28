
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from jobseekers.models import JobSeekerProfile
from recruiters.models import Company, RecruiterProfile

User = get_user_model()


class CustomUserManagerTests(TestCase):

    def test_create_user_with_email(self):
        user = User.objects.create_user(
            email="seeker@example.com",
            password="TestPass123"
        )

        self.assertEqual(user.email, "seeker@example.com")
        self.assertTrue(user.check_password("TestPass123"))
        self.assertEqual(user.role, User.Role.SEEKER)

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(
                email="",
                password="TestPass123"
            )

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email="admin@example.com",
            password="AdminPass123"
        )

        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.role, User.Role.ADMIN)


class AccountRegistrationTests(TestCase):

    def test_successful_registration(self):
        response = self.client.post(reverse("register"), {
            "first_name": "Naveen",
            "last_name": "K",
            "email": "newseeker@example.com",
            "password": "TestPass123",
            "confirm_password": "TestPass123",
        })

        self.assertRedirects(response, reverse("job_list"))

        user = User.objects.get(email="newseeker@example.com")

        self.assertEqual(user.role, User.Role.SEEKER)
        self.assertTrue(
            JobSeekerProfile.objects.filter(user=user).exists()
        )
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_registration_rejects_password_mismatch(self):
        response = self.client.post(reverse("register"), {
            "first_name": "Test",
            "email": "test@example.com",
            "password": "TestPass123",
            "confirm_password": "WrongPass123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(email="test@example.com").exists()
        )

    def test_registration_rejects_short_password(self):
        response = self.client.post(reverse("register"), {
            "first_name": "Test",
            "email": "test@example.com",
            "password": "123",
            "confirm_password": "123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            User.objects.filter(email="test@example.com").exists()
        )

    def test_registration_rejects_duplicate_email(self):
        User.objects.create_user(
            email="existing@example.com",
            password="TestPass123"
        )

        response = self.client.post(reverse("register"), {
            "first_name": "Test",
            "email": "existing@example.com",
            "password": "TestPass123",
            "confirm_password": "TestPass123",
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            User.objects.filter(
                email="existing@example.com"
            ).count(),
            1
        )


class AccountAuthenticationTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="login@example.com",
            password="TestPass123"
        )

    def test_login_with_valid_credentials(self):
        response = self.client.post(reverse("login"), {
            "email": "login@example.com",
            "password": "TestPass123",
        })

        self.assertRedirects(response, reverse("job_list"))
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_invalid_password(self):
        response = self.client.post(reverse("login"), {
            "email": "login@example.com",
            "password": "WrongPassword",
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_logout(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("job_list"))
        self.assertFalse(response.wsgi_request.user.is_authenticated)


class RecruiterRegistrationTests(TestCase):

    def test_recruiter_registration_success(self):
        response = self.client.post(
            reverse("recruiter_register"),
            {
                "email": "hr@example.com",
                "first_name": "Arun",
                "last_name": "Kumar",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "company_name": "Tech Solutions",
                "industry": "IT",
                "location": "Coimbatore",
                "designation": "HR Manager",
                "phone": "9876543210",
            }
        )

        user = User.objects.get(email="hr@example.com")

        self.assertEqual(user.role, User.Role.RECRUITER)

        self.assertTrue(
            RecruiterProfile.objects.filter(user=user).exists()
        )

        self.assertTrue(
            Company.objects.filter(name="Tech Solutions").exists()
        )

        self.assertRedirects(
            response,
            reverse("recruiter_dashboard")
        )

        self.assertTrue(
            response.wsgi_request.user.is_authenticated
        )

    def test_recruiter_password_mismatch(self):
        response = self.client.post(
            reverse("recruiter_register"),
            {
                "email": "hr@example.com",
                "first_name": "Arun",
                "password": "StrongPass123!",
                "confirm_password": "WrongPass123!",
                "company_name": "Tech Solutions",
            }
        )

        self.assertFalse(
            User.objects.filter(email="hr@example.com").exists()
        )
        self.assertEqual(response.status_code, 200)

    def test_recruiter_short_password(self):
        self.client.post(
            reverse("recruiter_register"),
            {
                "email": "hr@example.com",
                "first_name": "Arun",
                "password": "123",
                "confirm_password": "123",
                "company_name": "Tech Solutions",
            }
        )

        self.assertFalse(
            User.objects.filter(email="hr@example.com").exists()
        )

    def test_recruiter_duplicate_email(self):
        User.objects.create_user(
            email="hr@example.com",
            password="StrongPass123!",
            role=User.Role.SEEKER,
        )

        self.client.post(
            reverse("recruiter_register"),
            {
                "email": "hr@example.com",
                "first_name": "Arun",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "company_name": "Tech Solutions",
            }
        )

        self.assertEqual(
            User.objects.filter(email="hr@example.com").count(),
            1
        )

    def test_recruiter_registration_missing_company(self):
        self.client.post(
            reverse("recruiter_register"),
            {
                "email": "hr@example.com",
                "first_name": "Arun",
                "password": "StrongPass123!",
                "confirm_password": "StrongPass123!",
                "company_name": "",
            }
        )

        self.assertFalse(
            User.objects.filter(email="hr@example.com").exists()
        )
