from django.contrib import admin
from .models import SequenceSubmission, PredictionModel

# Register your models here.
@admin.register(PredictionModel)
class PredictionModelAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'updated_at')
    # Controls which columns appear on the model's changelist table.
    list_filter = ('is_active', 'created_at')
    # Adds side filters to narrow down large datasets by specific fields.
    search_fields = ('name', 'description')
    # Adds a search bar at the top of the admin page to query specific text/number fields.
    readonly_fields = ('created_at', 'updated_at') 
    # Makes specific fields uneditable in the admin view.

@admin.register(SequenceSubmission)
class SequenceSubmissionAdmin(admin.ModelAdmin):
    list_display = ('user', 'prediction_model','sequence', 'status', 'submit_date', 'result', 'result_date')
    list_filter = ('status', 'submit_date', 'result_date', 'prediction_model')
    search_fields = ('user__username', 'sequence')
    readonly_fields = ('submit_date',)
