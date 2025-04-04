from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import SequenceSubmission
from django.core.exceptions import ValidationError
from datetime import datetime, timezone
from django.utils.timezone import make_aware
from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Checkbox

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.is_active = True  # User can login but needs email verification for submissions
            user.save()
        return user

class SequenceSubmissionForm(forms.ModelForm):
    class Meta:
        model = SequenceSubmission
        fields = ['sequence']

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.user:
            # Check if email is verified
            if not self.user.userprofile.email_verified:
                raise ValidationError("You must verify your email address before submitting sequences.")
                
            # Check if user has already submitted today
            today = make_aware(datetime.now())
            today_submission = SequenceSubmission.objects.filter(
                user=self.user,
                submit_date__year=today.year,
                submit_date__month=today.month,
                submit_date__day=today.day
            ).exists()
            
            if today_submission:
                raise ValidationError("You have already submitted a sequence today. Please try again tomorrow.")
