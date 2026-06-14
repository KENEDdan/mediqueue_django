from django.urls import path
from . import views

urlpatterns = [
    path('reports/write/<int:appt_id>/',  views.write_medical_report,  name='write_medical_report'),
    path('reports/clinic/',               views.clinic_patient_records, name='clinic_patient_records'),
    path('walkin/',                        views.walkin_patient_list,    name='walkin_patient_list'),
    path('walkin/new/',                    views.walkin_patient_create,  name='walkin_patient_create'),
    path('walkin/<int:pk>/',              views.walkin_patient_detail,  name='walkin_patient_detail'),
]