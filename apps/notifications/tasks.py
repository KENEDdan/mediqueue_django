# apps/notifications/tasks.py
from celery import shared_task
from django.conf import settings


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, to: str, subject: str, template: str, context_data: dict):
    """
    Async email task. Retries up to 3 times on failure.
    context_data must be JSON-serialisable (no model instances — use PKs).
    """
    try:
        from apps.notifications.utils import send_email
        send_email(to=to, subject=subject, template=template, context=context_data)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def send_appointment_received_task(appointment_id: int):
    from apps.appointments.models import Appointment
    try:
        appt = Appointment.objects.select_related(
            'patient', 'clinic'
        ).get(pk=appointment_id)
        send_email_task.delay(
            to=appt.patient.email,
            subject=f'[MediQueue] Appointment Request Received — {appt.clinic.name}',
            template='emails/appointment_received.html',
            context_data={
                'patient_name': appt.patient.full_name,
                'clinic_name':  appt.clinic.name,
                'condition':    appt.condition_description[:200],
                'preferred_date': str(appt.preferred_date),
                'app_name': settings.APP_NAME,
            }
        )
    except Appointment.DoesNotExist:
        pass


@shared_task
def send_appointment_confirmed_task(appointment_id: int):
    from apps.appointments.models import Appointment
    try:
        appt = Appointment.objects.select_related(
            'patient', 'clinic', 'doctor__user', 'doctor__specialization'
        ).get(pk=appointment_id)
        send_email_task.delay(
            to=appt.patient.email,
            subject=f'[MediQueue] Appointment Confirmed — {appt.confirmed_date}',
            template='emails/appointment_confirmed.html',
            context_data={
                'patient_name':   appt.patient.full_name,
                'clinic_name':    appt.clinic.name,
                'doctor_name':    appt.doctor.user.full_name if appt.doctor else 'TBD',
                'confirmed_date': str(appt.confirmed_date),
                'confirmed_time': str(appt.confirmed_time_slot),
                'app_name': settings.APP_NAME,
            }
        )
    except Appointment.DoesNotExist:
        pass


@shared_task
def send_appointment_cancelled_task(appointment_id: int):
    from apps.appointments.models import Appointment
    try:
        appt = Appointment.objects.select_related('patient', 'clinic').get(pk=appointment_id)
        send_email_task.delay(
            to=appt.patient.email,
            subject=f'[MediQueue] Appointment Update — {appt.clinic.name}',
            template='emails/appointment_cancelled.html',
            context_data={
                'patient_name':  appt.patient.full_name,
                'clinic_name':   appt.clinic.name,
                'reason':        appt.rejection_note,
                'app_name': settings.APP_NAME,
            }
        )
    except Appointment.DoesNotExist:
        pass


@shared_task
def send_clinic_approved_task(clinic_id: int):
    from apps.clinics.models import Clinic
    try:
        clinic     = Clinic.objects.get(pk=clinic_id)
        admin_user = clinic.staff.filter(role='clinic_admin').first()
        if not admin_user:
            return
        send_email_task.delay(
            to=admin_user.email,
            subject=f"[MediQueue] Your clinic '{clinic.name}' has been approved! 🎉",
            template='emails/clinic_approved.html',
            context_data={
                'admin_name': admin_user.full_name,
                'clinic_name': clinic.name,
                'app_name': settings.APP_NAME,
            }
        )
    except Clinic.DoesNotExist:
        pass


@shared_task
def send_clinic_rejected_task(clinic_id: int, reason: str):
    from apps.clinics.models import Clinic
    try:
        clinic     = Clinic.objects.get(pk=clinic_id)
        admin_user = clinic.staff.filter(role='clinic_admin').first()
        if not admin_user:
            return
        send_email_task.delay(
            to=admin_user.email,
            subject=f"[MediQueue] Registration update for '{clinic.name}'",
            template='emails/clinic_rejected.html',
            context_data={
                'admin_name':  admin_user.full_name,
                'clinic_name': clinic.name,
                'reason':      reason,
                'app_name': settings.APP_NAME,
            }
        )
    except Clinic.DoesNotExist:
        pass


@shared_task
def send_admin_new_clinic_task(clinic_id: int):
    from apps.clinics.models import Clinic
    try:
        clinic     = Clinic.objects.get(pk=clinic_id)
        admin_user = clinic.staff.filter(role='clinic_admin').first()
        docs       = list(clinic.documents.values('doc_type', 'file_name'))
        send_email_task.delay(
            to=settings.ADMIN_EMAIL,
            subject=f'[MediQueue] New clinic pending review — {clinic.name}',
            template='emails/admin_new_clinic.html',
            context_data={
                'clinic_name':  clinic.name,
                'admin_name':   admin_user.full_name if admin_user else 'Unknown',
                'admin_email':  admin_user.email if admin_user else '',
                'phone':        clinic.phone,
                'plan':         clinic.get_subscription_plan_display(),
                'docs':         docs,
                'app_name': settings.APP_NAME,
            }
        )
    except Clinic.DoesNotExist:
        pass

@shared_task
def send_slot_proposed_task(appointment_id: int):
    from apps.appointments.models import Appointment
    try:
        appt = Appointment.objects.select_related('patient','clinic','doctor__user').get(pk=appointment_id)
        send_email_task.delay(
            to=appt.patient.email,
            subject=f'[MediQueue] Appointment Slot Proposed — {appt.clinic.name}',
            template='emails/slot_proposed.html',
            context_data={
                'patient_name':    appt.patient.full_name,
                'clinic_name':     appt.clinic.name,
                'doctor_name':     appt.doctor.user.full_name if appt.doctor else 'TBD',
                'proposed_date':   str(appt.proposed_date),
                'proposed_time':   str(appt.proposed_time_slot),
                'proposal_message': appt.proposal_message,
                'booking_fee':     str(appt.booking_fee),
                'currency':        appt.booking_fee_currency,
                'app_name':        settings.APP_NAME,
            }
        )
    except Exception:
        pass


@shared_task
def send_payment_submitted_task(appointment_id: int):
    from apps.appointments.models import Appointment
    try:
        appt = Appointment.objects.select_related('patient','clinic','receptionist').get(pk=appointment_id)
        if appt.receptionist:
            send_email_task.delay(
                to=appt.receptionist.email,
                subject=f'[MediQueue] Payment submitted — {appt.patient.full_name}',
                template='emails/payment_submitted.html',
                context_data={
                    'patient_name':  appt.patient.full_name,
                    'clinic_name':   appt.clinic.name,
                    'amount':        str(appt.booking_fee),
                    'currency':      appt.booking_fee_currency,
                    'app_name':      settings.APP_NAME,
                }
            )
    except Exception:
        pass


@shared_task
def send_report_ready_task(report_id: int):
    from apps.records.models import MedicalReport
    try:
        report = MedicalReport.objects.select_related('patient','clinic','doctor__user').get(pk=report_id)
        send_email_task.delay(
            to=report.patient.email,
            subject=f'[MediQueue] Your medical report is ready — {report.clinic.name}',
            template='emails/report_ready.html',
            context_data={
                'patient_name': report.patient.full_name,
                'doctor_name':  report.doctor.user.full_name,
                'clinic_name':  report.clinic.name,
                'diagnosis':    report.diagnosis[:200],
                'app_name':     settings.APP_NAME,
            }
        )
    except Exception:
        pass