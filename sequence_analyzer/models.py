from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MaxLengthValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email_verified = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid.uuid4)

    def __str__(self):
        return f"{self.user.username}'s profile"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()

class SequenceSubmission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sequence = models.CharField(
        max_length=130,
        validators=[
            RegexValidator(
                regex='^[acdefghiklmnpqrstvwxyACDEFGHIKLMNPQRSTVWY]+$',
                message='Sequence must contain only valid amino acid letters (ACDEFGHIKLMNPQRSTVWY)',
                code='invalid_sequence'
            ),
            MaxLengthValidator(130)
        ]
    )
    status = models.CharField(
        max_length=10,
        choices=[('pending', 'Pending'), ('done', 'Done')],
        default='pending'
    )
    submit_date = models.DateTimeField(auto_now_add=True)
    result = models.FloatField(default=0)
    result_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submit_date']

    def __str__(self):
        return f"Sequence submission by {self.user.username} on {self.submit_date}"