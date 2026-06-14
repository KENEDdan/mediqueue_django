from django.contrib import admin
from .models import MedicalReport, WalkInPatient, WalkInVisit

@admin.register(MedicalReport)
class MedicalReportAdmin(admin.ModelAdmin):
    list_display  = ['patient', 'doctor', 'clinic', 'diagnosis', 'created_at']
    list_filter   = ['clinic', 'is_shared_with_patient']
    search_fields = ['patient__full_name', 'diagnosis', 'doctor__user__full_name']

@admin.register(WalkInPatient)
class WalkInPatientAdmin(admin.ModelAdmin):
    list_display  = ['full_name', 'clinic', 'phone', 'blood_group', 'created_at']
    list_filter   = ['clinic', 'gender', 'blood_group']
    search_fields = ['full_name', 'phone', 'email']

@admin.register(WalkInVisit)
class WalkInVisitAdmin(admin.ModelAdmin):
    list_display  = ['patient', 'clinic', 'doctor', 'visit_date', 'diagnosis']
    list_filter   = ['clinic', 'visit_date']
    search_fields = ['patient__full_name', 'diagnosis']