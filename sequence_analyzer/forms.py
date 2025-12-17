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

class FastaSubmissionForm(forms.Form):
    fasta_sequences = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 10,
            'cols': 80,
            'placeholder': '>seq1\nACDEFGHIKLMNPQRSTVWY\n>seq2\nCDEFGHIKLMNPQRSTVWY\n...'
        }),
        label='FASTA Sequences',
        help_text='Enter up to 10 sequences in FASTA format. Each sequence must be ≤130 amino acids.'
    )

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def parse_fasta(self, fasta_text):
        """Parse FASTA format text and return list of (title, sequence) tuples"""
        sequences = []
        current_title = None
        current_sequence = ""
        
        for line in fasta_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('>'):
                # Save previous sequence if exists
                if current_title and current_sequence:
                    sequences.append((current_title, current_sequence.upper()))
                
                # Start new sequence
                current_title = line[1:].strip()  # Remove '>' and whitespace
                if not current_title:
                    current_title = f"seq_{len(sequences) + 1}"
                current_sequence = ""
            else:
                # Add to current sequence
                current_sequence += line.replace(' ', '').replace('\t', '')
        
        # Don't forget the last sequence
        if current_title and current_sequence:
            sequences.append((current_title, current_sequence.upper()))
            
        return sequences

    def clean_fasta_sequences(self):
        fasta_text = self.cleaned_data['fasta_sequences']
        
        if not fasta_text.strip():
            raise ValidationError("Please enter sequences in FASTA format.")
        
        # Parse FASTA
        try:
            sequences = self.parse_fasta(fasta_text)
        except Exception as e:
            raise ValidationError(f"Error parsing FASTA format: {str(e)}")
        
        if not sequences:
            raise ValidationError("No valid sequences found. Please check your FASTA format.")
        
        if len(sequences) > 10:
            raise ValidationError("Maximum 10 sequences allowed per submission.")
        
        # Validate each sequence
        amino_acid_pattern = r'^[ACDEFGHIKLMNPQRSTVWY]+$'
        for i, (title, sequence) in enumerate(sequences, 1):
            if len(sequence) > 130:
                raise ValidationError(f"Sequence {i} ({title}) is too long. Maximum 130 amino acids allowed.")
            
            if not sequence:
                raise ValidationError(f"Sequence {i} ({title}) is empty.")
            
            import re
            if not re.match(amino_acid_pattern, sequence):
                raise ValidationError(f"Sequence {i} ({title}) contains invalid characters. Only amino acid letters (ACDEFGHIKLMNPQRSTVWY) are allowed.")
        
        return sequences

    def clean(self):
        cleaned_data = super().clean()
        if self.user:
            # Check if email is verified
            if not self.user.userprofile.email_verified:
                raise ValidationError("You must verify your email address before submitting sequences.")
                
            # Check daily submission limit (now 10 sequences per day)
            today = make_aware(datetime.now())
            today_submissions_count = SequenceSubmission.objects.filter(
                user=self.user,
                submit_date__year=today.year,
                submit_date__month=today.month,
                submit_date__day=today.day
            ).count()
            
            sequences = cleaned_data.get('fasta_sequences', [])
            if isinstance(sequences, list):
                total_new_sequences = len(sequences)
                if today_submissions_count + total_new_sequences > 10:
                    remaining = 10 - today_submissions_count
                    raise ValidationError(f"Daily limit exceeded. You can submit {remaining} more sequences today.")
        
        return cleaned_data

# Keep the old form for backward compatibility if needed
class SequenceSubmissionForm(forms.ModelForm):
    class Meta:
        model = SequenceSubmission
        fields = ['title', 'sequence']

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
