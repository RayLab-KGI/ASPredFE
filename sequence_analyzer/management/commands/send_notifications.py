# your_app_name/management/commands/send_notifications.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from sequence_analyzer.models import SequenceSubmission

class Command(BaseCommand):
    help = 'Checks for updated submissions and emails notifications'

    def handle(self, *args, **options):
        # 1. Fetch updates that haven't been emailed yet
        need_to_email_submissions = SequenceSubmission.objects.exclude(result_date__isnull=True).filter(email_sent=False)
        
        if not need_to_email_submissions.exists():
            self.stdout.write(self.style.SUCCESS("No new updates found."))
            return

        self.stdout.write(f"Found {need_to_email_submissions.count()} updates. Sending emails...")

        # 2. Loop through and send notifications
        for submission in need_to_email_submissions:
            send_mail(
                subject=f"Update Notification: {submission.title} Results",
                message=f"The submission '{submission.title}' now has results.",
                from_email=None, # Uses DEFAULT_FROM_EMAIL
                recipient_list=[submission.user.email], 
                fail_silently=False,
            )
            
            # 3. Mark as processed so they aren't emailed next time
            submission.email_sent = True
            submission.save()

        self.stdout.write(self.style.SUCCESS("All notification emails dispatched successfully."))
