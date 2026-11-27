from django.contrib import admin
from .models import (
    Skill,
    JobSeekerProfile,
    Education,
    Experience,
    Resume,
)


admin.site.register(Skill)
admin.site.register(JobSeekerProfile)
admin.site.register(Education)
admin.site.register(Experience)
admin.site.register(Resume)