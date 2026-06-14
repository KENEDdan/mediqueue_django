from django.urls import path
from . import views

urlpatterns = [
    path('clinics/',          views.ClinicListAPI.as_view(),        name='api_clinics'),
    path('specializations/',  views.SpecializationListAPI.as_view(),name='api_specs'),
    path('my/appointments/',  views.PatientAppointmentsAPI.as_view(),name='api_my_appts'),
    path('slots/',            views.available_slots_api,            name='api_slots'),
]