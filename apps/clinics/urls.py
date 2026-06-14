from django.urls import path
from . import views

urlpatterns = [
    path('register/',        views.register_clinic,        name='register_clinic'),
    path('<slug:slug>/',     views.clinic_detail,          name='clinic_detail'),

    # Clinic Admin
    path('admin/dashboard/', views.clinic_admin_dashboard, name='clinic_admin_dashboard'),
    path('admin/staff/<str:role>/', views.manage_staff,    name='manage_staff'),
    path('admin/staff/<str:role>/add/', views.add_staff,   name='add_staff'),
    path('admin/staff/<int:user_id>/toggle/', views.toggle_staff, name='toggle_staff'),
    path('admin/doctors/pending/',  views.pending_doctors,          name='clinic_admin_pending_doctors'),
    path('admin/doctors/<int:user_id>/approve/', views.approve_doctor, name='approve_doctor'),
    path('admin/doctors/<int:user_id>/reject/',  views.reject_doctor_account, name='reject_doctor_account'),
    path('admin/services/',         views.manage_services,  name='manage_services'),
    path('admin/services/<int:service_id>/remove/', views.remove_service, name='remove_service'),
    path('admin/settings/',         views.clinic_settings,  name='clinic_settings'),
    path('admin/subscription/',     views.subscription_page,name='subscription_page'),
    path('admin/subscription/upgrade/', views.upgrade_plan, name='upgrade_plan'),
    path('admin/gallery/', views.manage_gallery, name='manage_gallery'),
]