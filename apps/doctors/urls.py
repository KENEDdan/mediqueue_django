from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',             views.doctor_dashboard,    name='doctor_dashboard'),
    path('appointments/',          views.doctor_appointments, name='doctor_appointments'),
    path('appointments/<int:appt_id>/mark/<str:new_status>/', views.mark_appointment, name='mark_appointment'),
    path('appointments/<int:appt_id>/note/', views.save_doctor_note, name='save_doctor_note'),
    path('schedule/',              views.doctor_schedule,     name='doctor_schedule'),
    path('blocked-dates/',         views.doctor_blocked_dates,name='doctor_blocked_dates'),
]