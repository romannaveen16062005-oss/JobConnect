from django import forms

from .models import Job


class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = [
            "title",
            "description",
            "requirements",
            "responsibilities",
            "location",
            "is_remote",
            "job_type",
            "experience_level",
            "salary_min",
            "salary_max",
            "vacancies",
            "application_deadline",
        ]

        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
            "responsibilities": forms.Textarea(attrs={"rows": 4}),
            "application_deadline": forms.DateInput(attrs={"type": "date"}),
        }