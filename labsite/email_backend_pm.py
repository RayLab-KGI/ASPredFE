from django.core.mail.backends.smtp import EmailBackend

class CustomEmailBackend(EmailBackend):
    def send_messages(self, email_messages):
        for message in email_messages:
            # Add the custom header to all outgoing emails
            message.extra_headers = message.extra_headers or {}
            message.extra_headers["X-PM-Message-Stream"] = "outbound"
        return super().send_messages(email_messages)
