from django.contrib import admin
from .models import Clinic, ClinicDocument, ClinicService, Specialization

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display  = ['name', 'approval_status', 'subscription_plan', 'subscription_status', 'is_active']
    list_filter   = ['approval_status', 'subscription_plan', 'subscription_status']
    search_fields = ['name', 'email', 'slug']

@admin.register(ClinicDocument)
class ClinicDocumentAdmin(admin.ModelAdmin):
    list_display = ['clinic', 'doc_type', 'file_name', 'uploaded_at']

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'description']
    search_fields = ['name']

admin.site.register(ClinicService)