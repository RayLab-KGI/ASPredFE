from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.urls import reverse
from .forms import CustomUserCreationForm, SequenceSubmissionForm, FastaSubmissionForm, ModelDropdownForm
from .models import SequenceSubmission, UserProfile, PredictionModel

# Create your views here.

def home(request):
    return render(request, 'sequence_analyzer/home.html')

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            
            # Send verification email
            verification_url = request.build_absolute_uri(
                reverse('verify_email', args=[user.userprofile.verification_token])
            )
            html_message = render_to_string(
                'sequence_analyzer/email/verify_email.html',
                {'user': user, 'verification_url': verification_url}
            )
            plain_message = strip_tags(html_message)
            
            send_mail(
                'Verify your email address',
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            messages.success(
                request,
                "Registration successful! Please check your email to verify your account before submitting sequences."
            )
            return redirect('dashboard')
    else:
        form = CustomUserCreationForm()
    return render(request, 'sequence_analyzer/register.html', {'form': form})

def verify_email(request, token):
    user_profile = get_object_or_404(UserProfile, verification_token=token)
    if not user_profile.email_verified:
        user_profile.email_verified = True
        user_profile.save()
        messages.success(request, "Email verified successfully! You can now submit sequences.")
    else:
        messages.info(request, "Email was already verified.")
    return redirect('dashboard')

@login_required
def dashboard(request):
    return render(request, 'sequence_analyzer/dashboard.html')

@login_required
def submit_sequence(request):
    if not request.user.userprofile.email_verified:
        messages.error(request, "Please verify your email address before submitting sequences.")
        return redirect('dashboard')
    
    # Calculate today's submission count
    from datetime import datetime
    from django.utils.timezone import make_aware
    today = make_aware(datetime.now())
    today_submissions_count = SequenceSubmission.objects.filter(
        user=request.user,
        submit_date__year=today.year,
        submit_date__month=today.month,
        submit_date__day=today.day
    ).count()
        
    if request.method == 'POST':
        # 1. Bind POST data to both forms using prefixes
        model_form = ModelDropdownForm(request.POST, prefix='model', user=request.user)
        sequence_form = FastaSubmissionForm(request.POST, prefix='sequence', user=request.user)
                
        if model_form.is_valid() and sequence_form.is_valid():
            selected_model = model_form.cleaned_data['prediction_model']
            sequences = sequence_form.cleaned_data['fasta_sequences']
            created_count = 0

            for title, sequence in sequences:
                SequenceSubmission.objects.create(
                    user=request.user,
                    prediction_model=selected_model,
                    title=title,
                    sequence=sequence
                )
                created_count += 1

            messages.success(request, f"{created_count} sequence(s) submitted successfully!")
            return redirect('view_submissions')
    else:
        model_form = ModelDropdownForm(prefix='model', user=request.user)
        sequence_form = FastaSubmissionForm(prefix='sequence', user=request.user)
    
    context = {
        'model_form': model_form,
        'sequence_form': sequence_form,
        'today_submissions_count': today_submissions_count,
        'remaining_submissions': 10 - today_submissions_count,
    }
    return render(request, 'sequence_analyzer/submit_sequence.html', context)

@login_required
def view_submissions(request):
    submissions = SequenceSubmission.objects.filter(user=request.user)
    return render(request, 'sequence_analyzer/view_submissions.html', {'submissions': submissions})
