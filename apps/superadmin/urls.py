from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    path('',                        views.dashboard,       name='dashboard'),
    path('pending/',                views.pending_clinics, name='pending_clinics'),
    path('clinics/',                views.all_clinics,     name='all_clinics'),
    path('clinics/<int:clinic_id>/approve/', views.approve_clinic, name='approve_clinic'),
    path('clinics/<int:clinic_id>/reject/',  views.reject_clinic,  name='reject_clinic'),
    path('clinics/<int:clinic_id>/delete/',  views.delete_clinic,  name='delete_clinic'),
    path('clinics/<int:clinic_id>/restore/', views.restore_clinic, name='restore_clinic'),
    path('users/',                  views.all_users,       name='all_users'),
    path('stats/',                  views.platform_stats,  name='stats'),
    path('pending/<int:clinic_id>/approve/', views.approve_clinic, name='approve_clinic'),
    path('pending/<int:clinic_id>/reject/',  views.reject_clinic,  name='reject_clinic'),
]