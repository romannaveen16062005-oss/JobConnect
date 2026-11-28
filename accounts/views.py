
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

from .models import User
from jobseekers.models import JobSeekerProfile

from django.db import transaction
from recruiters.models import Company, RecruiterProfile


def register(request):
    if request.user.is_authenticated:
        return redirect("job_list")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([email, first_name, password, confirm_password]):
            messages.error(request, "Please fill all required fields.")

        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")

        elif len(password) < 8:
            messages.error(request, "Password must contain at least 8 characters.")

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already registered.")

        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.SEEKER,
            )

            JobSeekerProfile.objects.create(user=user)
            login(request, user)

            messages.success(request, "Registration successful!")
            return redirect("job_list")

    return render(request, "accounts/register.html")


def user_login(request):
    if request.user.is_authenticated:
        return redirect("job_list")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        user = authenticate(
            request,
            email=email,
            password=password
        )

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account is inactive.")
            else:
                login(request, user)
                return redirect("job_list")
        else:
            messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login.html")


@login_required
def user_logout(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "You have been logged out.")
        return redirect("job_list")
    return render(request, "accounts/logout.html")


def recruiter_register(request):
    if request.user.is_authenticated:
        return redirect("job_list")

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        company_name = request.POST.get("company_name", "").strip()
        industry = request.POST.get("industry", "").strip()
        location = request.POST.get("location", "").strip()
        designation = request.POST.get("designation", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not all([
            email, first_name, password, confirm_password,
            company_name
        ]):
            messages.error(request, "Please fill all required fields.")

        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")

        elif len(password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters."
            )

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "Email already registered.")

        else:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    role=User.Role.RECRUITER,
                )

                company = Company.objects.create(
                    name=company_name,
                    industry=industry,
                    location=location,
                )

                RecruiterProfile.objects.create(
                    user=user,
                    company=company,
                    designation=designation,
                    phone=phone,
                )

            login(request, user)

            messages.success(
                request,
                "Recruiter registration successful!"
            )
            return redirect("recruiter_dashboard")

    return render(
        request,
        "accounts/recruiter_register.html"
    )