
from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from jobseekers.models import (
    Skill,
    JobSeekerProfile,
    Education,
    Experience,
    Resume,
)


class JobSeekerModelTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="seeker@example.com",
            password="TestPass123",
            role=User.Role.SEEKER,
        )

        cls.profile = JobSeekerProfile.objects.create(
            user=cls.user,
            phone="9876543210",
            location="Coimbatore",
            headline="Python Developer",
            summary="Full Stack Python Developer",
        )

    def test_create_jobseeker_profile(self):
        self.assertEqual(self.profile.user, self.user)
        self.assertEqual(self.profile.location, "Coimbatore")

    def test_create_skill_and_assign_to_profile(self):
        skill = Skill.objects.create(name="Python")
        self.profile.skills.add(skill)

        self.assertIn(skill, self.profile.skills.all())

    def test_duplicate_skill_name_rejected(self):
        from django.db import IntegrityError, transaction

        Skill.objects.create(name="Python")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Skill.objects.create(name="Python")

    def test_create_education(self):
        education = Education.objects.create(
            profile=self.profile,
            institution="ABC College",
            degree="B.Sc",
            field_of_study="Computer Science",
            start_date=date(2022, 6, 1),
            end_date=date(2025, 5, 31),
            grade="First Class",
        )

        self.assertEqual(education.profile, self.profile)
        self.assertEqual(education.degree, "B.Sc")

    def test_create_experience(self):
        experience = Experience.objects.create(
            profile=self.profile,
            job_title="Python Developer",
            company_name="Tech Company",
            start_date=date(2025, 6, 1),
            currently_working=True,
        )

        self.assertEqual(experience.profile, self.profile)
        self.assertTrue(experience.currently_working)

    def test_create_resume(self):
        uploaded_file = SimpleUploadedFile(
            "resume.txt",
            b"Sample resume content",
            content_type="text/plain",
        )

        resume = Resume.objects.create(
            profile=self.profile,
            title="My Resume",
            file=uploaded_file,
            is_default=True,
        )

        self.assertEqual(resume.profile, self.profile)
        self.assertTrue(resume.is_default)
        self.assertTrue(resume.file.name.endswith(".txt"))

    def test_profile_deletion_cascades_related_records(self):
        skill = Skill.objects.create(name="Django")
        self.profile.skills.add(skill)

        Education.objects.create(
            profile=self.profile,
            institution="ABC College",
            degree="B.Sc",
        )

        Experience.objects.create(
            profile=self.profile,
            job_title="Developer",
            company_name="ABC Company",
            start_date=date(2025, 1, 1),
        )

        self.profile.delete()

        self.assertEqual(Education.objects.count(), 0)
        self.assertEqual(Experience.objects.count(), 0)
        self.assertEqual(JobSeekerProfile.objects.count(), 0)
        self.assertTrue(Skill.objects.filter(pk=skill.pk).exists())


class ResumeUploadTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="resumeuser@example.com",
            password="TestPass123",
            role=User.Role.SEEKER,
        )

        self.profile = JobSeekerProfile.objects.create(
            user=self.user,
        )

        self.client.force_login(self.user)

    def test_seeker_can_upload_valid_pdf_resume(self):
        uploaded_file = SimpleUploadedFile(
            "resume.pdf",
            b"%PDF-1.4 Sample PDF content",
            content_type="application/pdf",
        )

        response = self.client.post(
            reverse("upload_resume"),
            {
                "title": "My Resume",
                "file": uploaded_file,
            },
        )

        self.assertRedirects(
            response,
            reverse("upload_resume"),
        )

        resume = self.profile.resumes.get()

        self.assertEqual(resume.title, "My Resume")
        self.assertTrue(resume.is_default)

    def test_invalid_file_extension_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "resume.txt",
            b"Sample text",
            content_type="text/plain",
        )

        self.client.post(
            reverse("upload_resume"),
            {
                "title": "Invalid Resume",
                "file": uploaded_file,
            },
        )

        self.assertEqual(Resume.objects.count(), 0)

    def test_invalid_pdf_signature_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "fake.pdf",
            b"This is not a PDF file",
            content_type="application/pdf",
        )

        self.client.post(
            reverse("upload_resume"),
            {
                "title": "Fake PDF",
                "file": uploaded_file,
            },
        )

        self.assertEqual(Resume.objects.count(), 0)

    def test_resume_over_five_mb_is_rejected(self):
        uploaded_file = SimpleUploadedFile(
            "large.pdf",
            b"%PDF-" + (b"A" * (5 * 1024 * 1024)),
            content_type="application/pdf",
        )

        self.client.post(
            reverse("upload_resume"),
            {
                "title": "Large Resume",
                "file": uploaded_file,
            },
        )

        self.assertEqual(Resume.objects.count(), 0)

    def test_recruiter_cannot_upload_resume(self):
        recruiter = User.objects.create_user(
            email="uploadrecruiter@example.com",
            password="TestPass123",
            role=User.Role.RECRUITER,
        )

        self.client.force_login(recruiter)

        response = self.client.get(reverse("upload_resume"))

        self.assertRedirects(response, reverse("job_list"))
        self.assertEqual(Resume.objects.count(), 0)

    def test_new_resume_becomes_default(self):
        old_resume = Resume.objects.create(
            profile=self.profile,
            title="Old Resume",
            file=SimpleUploadedFile(
                "old.pdf",
                b"%PDF-1.4 Old resume",
            ),
            is_default=True,
        )

        new_resume = SimpleUploadedFile(
            "new.pdf",
            b"%PDF-1.4 New resume",
            content_type="application/pdf",
        )

        self.client.post(
            reverse("upload_resume"),
            {
                "title": "New Resume",
                "file": new_resume,
            },
        )

        old_resume.refresh_from_db()

        latest_resume = self.profile.resumes.get(
            title="New Resume"
        )

        self.assertFalse(old_resume.is_default)
        self.assertTrue(latest_resume.is_default)
