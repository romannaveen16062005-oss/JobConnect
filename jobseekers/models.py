
from django.conf import settings
from django.db import models


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class JobSeekerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="jobseeker_profile"
    )
    phone = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    headline = models.CharField(max_length=255, blank=True)
    summary = models.TextField(blank=True)
    profile_picture = models.ImageField(
        upload_to="profiles/",
        null=True,
        blank=True
    )
    skills = models.ManyToManyField(
        Skill,
        blank=True,
        related_name="jobseekers"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.email} - Job Seeker"


class Education(models.Model):
    profile = models.ForeignKey(
        JobSeekerProfile,
        on_delete=models.CASCADE,
        related_name="educations"
    )
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.degree} - {self.institution}"


class Experience(models.Model):
    profile = models.ForeignKey(
        JobSeekerProfile,
        on_delete=models.CASCADE,
        related_name="experiences"
    )
    job_title = models.CharField(max_length=150)
    company_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.job_title} - {self.company_name}"


class Resume(models.Model):
    profile = models.ForeignKey(
        JobSeekerProfile,
        on_delete=models.CASCADE,
        related_name="resumes"
    )
    title = models.CharField(max_length=150)
    file = models.FileField(upload_to="resumes/")
    is_default = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.profile.user.email}"
