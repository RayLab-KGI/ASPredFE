from django.contrib import admin
from .models import SequenceSubmission

# Register your models here.

@admin.register(SequenceSubmission)
class SequenceSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'sequence', 'status', 'submit_date', 'result', 'result_date')
    list_filter = ('status', 'submit_date', 'result_date')
    search_fields = ('user__username', 'sequence')
    readonly_fields = ('submit_date',)
