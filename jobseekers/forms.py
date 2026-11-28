
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from django import forms

from .models import Resume


MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}


def validate_resume_file(uploaded_file):
    extension = Path(uploaded_file.name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise forms.ValidationError(
            "Only PDF, DOC, and DOCX files are allowed."
        )

    if uploaded_file.size > MAX_RESUME_SIZE:
        raise forms.ValidationError(
            "Resume file size must not exceed 5 MB."
        )

    uploaded_file.seek(0)
    header = uploaded_file.read(8)
    uploaded_file.seek(0)

    if extension == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise forms.ValidationError("Invalid PDF file.")

    elif extension == ".doc":
        if header != bytes.fromhex("D0CF11E0A1B11AE1"):
            raise forms.ValidationError("Invalid DOC file.")

    elif extension == ".docx":
        try:
            with ZipFile(uploaded_file) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise forms.ValidationError("Invalid DOCX file.")
        except (BadZipFile, OSError):
            raise forms.ValidationError("Invalid DOCX file.")
        finally:
            uploaded_file.seek(0)


class ResumeUploadForm(forms.ModelForm):
    class Meta:
        model = Resume
        fields = ["title", "file"]

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if uploaded_file:
            validate_resume_file(uploaded_file)

        return uploaded_file
