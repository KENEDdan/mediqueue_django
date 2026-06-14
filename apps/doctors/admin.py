from django.contrib import admin
from .models import Doctor, DoctorSchedule, DoctorBlockedDate

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display  = ['user', 'clinic', 'specialization', 'is_accepting_patients']
    list_filter   = ['clinic', 'specialization', 'is_accepting_patients']
    search_fields = ['user__full_name', 'license_number']

admin.site.register(DoctorSchedule)
admin.site.register(DoctorBlockedDate)