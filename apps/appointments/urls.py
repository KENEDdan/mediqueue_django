from django.urls import path
from . import views

urlpatterns = [
    # Patient
    path('book/',                              views.book_appointment,         name='book_appointment'),
    path('my/',                                views.patient_dashboard,        name='patient_dashboard'),
    path('my/reports/',                        views.patient_reports,          name='patient_reports'),
    path('proposal/<int:appt_id>/respond/',    views.patient_respond_proposal, name='patient_respond_proposal'),
    path('pay/<int:appt_id>/',                 views.patient_pay_booking,      name='patient_pay_booking'),

    # Receptionist
    path('receptionist/',                      views.receptionist_dashboard,   name='receptionist_dashboard'),
    path('receptionist/pending/',              views.pending_appointments,     name='pending_appointments'),
    path('receptionist/all/',                  views.all_appointments,         name='all_appointments'),
    path('receptionist/<int:appt_id>/propose/',views.propose_appointment,      name='propose_appointment'),
    path('receptionist/<int:appt_id>/reject/', views.reject_appointment,       name='reject_appointment'),
    path('receptionist/payments/',             views.payment_queue,            name='payment_queue'),
    path('receptionist/payments/<int:appt_id>/verify/', views.verify_payment, name='verify_payment'),
    path('api/slots/',                         views.get_doctor_slots,         name='get_doctor_slots'),
    path('my/reports/', views.patient_reports, name='patient_reports'),
    path('my/<int:appt_id>/cancel/', views.patient_cancel_appointment, name='patient_cancel_appointment'),
]