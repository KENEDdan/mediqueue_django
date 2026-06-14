from django.urls import path
from . import views
from django.views.generic import TemplateView

urlpatterns = [
    path('',               views.landing,          name='landing'),
    path('login/',         views.patient_login,    name='patient_login'),
    path('staff-login/',   views.staff_login,      name='staff_login'),
    path('register/',      views.register_patient, name='register_patient'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('logout/',        views.user_logout,      name='logout'),
    path('dashboard/',     views.dashboard,        name='dashboard'),
    path('verify-2fa/', views.verify_2fa, name='verify_2fa'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    path('health/', views.health_check, name='health_check'),
    path('privacy/',  TemplateView.as_view(template_name='legal/privacy_policy.html'),  name='privacy_policy'),
    path('terms/',    TemplateView.as_view(template_name='legal/terms_of_service.html'),name='terms_of_service'),
    path('cookies/',  TemplateView.as_view(template_name='legal/cookie_policy.html'),   name='cookie_policy'),
]