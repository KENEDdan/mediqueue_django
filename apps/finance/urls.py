from django.urls import path
from . import views

urlpatterns = [
    # Superadmin
    path('superadmin/',              views.superadmin_finance,           name='superadmin_finance'),
    path('superadmin/record/',       views.record_subscription_payment,  name='record_subscription_payment'),

    # Clinic
    path('clinic/',                  views.clinic_finance,               name='clinic_finance'),
    path('clinic/payout-setup/',     views.setup_payout_account,         name='setup_payout_account'),

    # Receptionist
    path('receptionist/payments/',   views.receptionist_payments,        name='receptionist_payments'),
]