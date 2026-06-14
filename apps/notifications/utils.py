# apps/notifications/utils.py
"""
Email + in-app notification utilities.
"""
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.template.loader import render_to_string


def send_email(to: str, subject: str, template: str, context: dict) -> tuple:
    """Direct send. context must be JSON-serialisable (strings/numbers only)."""
    if not settings.EMAIL_HOST_PASSWORD:
        print(f'[Email] Dev-mode → {to}: {subject}')
        return True, ''
    try:
        html_body = render_to_string(template, context)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = settings.DEFAULT_FROM_EMAIL
        msg['To']      = to
        msg.attach(MIMEText(html_body, 'html'))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            server.starttls(context=ctx)
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.sendmail(settings.EMAIL_HOST_USER, to, msg.as_string())
        return True, ''
    except Exception as e:
        print(f'[Email] Failed → {to}: {e}')
        return False, str(e)


def notify_user(user, type, title, message, link='', send_email_too=True,
                 email_subject=None, email_template=None, email_context=None):
    """
    Single function for ANY notification: creates in-app Notification
    AND (optionally) sends an email via Celery.
    """
    from .models import Notification
    Notification.objects.create(
        user=user, type=type, title=title, message=message, link=link
    )

    if send_email_too and email_template:
        ctx = dict(email_context or {})
        ctx.setdefault('name', user.full_name)
        ctx.setdefault('title', title)
        ctx.setdefault('message', message)
        ctx.setdefault('app_name', settings.APP_NAME)
        try:
            from .tasks import send_email_task
            send_email_task.delay(
                to=user.email,
                subject=email_subject or f'[{settings.APP_NAME}] {title}',
                template=email_template,
                context_data=ctx,
            )
        except Exception as e:
            # Fallback to direct send if Celery unavailable
            print(f'[Notify] Celery unavailable, sending directly: {e}')
            send_email(user.email, email_subject or f'[{settings.APP_NAME}] {title}',
                       email_template, ctx)


def notify_appointment_received(appt):
    notify_user(
        user=appt.patient, type='appointment',
        title='Appointment request received',
        message=(
            f'Your appointment request to {appt.clinic.name} has been received.\n\n'
            f'A receptionist will review it and propose a doctor and time slot shortly.'
        ),
        link='/appointments/my/',
        email_subject=f'[MediQueue] Appointment request received — {appt.clinic.name}',
        email_template='emails/appointment_received.html',
        email_context={
            'patient_name':   appt.patient.full_name,
            'clinic_name':    appt.clinic.name,
            'condition':      appt.condition_description[:200],
            'preferred_date': str(appt.preferred_date),
        }
    )


def notify_slot_proposed(appt):
    notify_user(
        user=appt.patient, type='appointment',
        title='New appointment slot proposed',
        message=(
            f'{appt.clinic.name} proposed an appointment with '
            f'Dr. {appt.doctor.user.full_name if appt.doctor else "TBD"} '
            f'on {appt.proposed_date} at {appt.proposed_time_slot}.\n'
            f'Booking fee: {appt.booking_fee_currency} {appt.booking_fee}.\n\n'
            f'Please log in to accept or decline.'
        ),
        link=f'/appointments/proposal/{appt.pk}/respond/',
        email_subject=f'[MediQueue] Appointment slot proposed — {appt.clinic.name}',
        email_template='emails/slot_proposed.html',
        email_context={
            'patient_name':     appt.patient.full_name,
            'clinic_name':      appt.clinic.name,
            'doctor_name':      appt.doctor.user.full_name if appt.doctor else 'TBD',
            'proposed_date':    str(appt.proposed_date),
            'proposed_time':    str(appt.proposed_time_slot),
            'proposal_message': appt.proposal_message,
            'booking_fee':      str(appt.booking_fee),
            'currency':         appt.booking_fee_currency,
        }
    )


def notify_appointment_confirmed(appt):
    notify_user(
        user=appt.patient, type='appointment',
        title='Appointment confirmed ✅',
        message=(
            f'Your appointment at {appt.clinic.name} with '
            f'Dr. {appt.doctor.user.full_name if appt.doctor else ""} '
            f'is confirmed for {appt.confirmed_date} at {appt.confirmed_time_slot}.\n\n'
            f'Please arrive 10 minutes early.'
        ),
        link='/appointments/my/',
        email_subject=f'[MediQueue] Appointment confirmed — {appt.clinic.name}',
        email_template='emails/appointment_confirmed.html',
        email_context={
            'patient_name':   appt.patient.full_name,
            'clinic_name':    appt.clinic.name,
            'doctor_name':    appt.doctor.user.full_name if appt.doctor else '',
            'confirmed_date': str(appt.confirmed_date),
            'confirmed_time': str(appt.confirmed_time_slot),
        }
    )


def notify_appointment_cancelled(appt):
    notify_user(
        user=appt.patient, type='appointment',
        title='Appointment update',
        message=(
            f'Your appointment request to {appt.clinic.name} was cancelled.\n\n'
            f'Reason: {appt.rejection_note or "Not specified"}'
        ),
        link='/appointments/my/',
        email_subject=f'[MediQueue] Appointment update — {appt.clinic.name}',
        email_template='emails/appointment_cancelled.html',
        email_context={
            'patient_name': appt.patient.full_name,
            'clinic_name':  appt.clinic.name,
            'reason':       appt.rejection_note,
        }
    )


def notify_medical_report_ready(report):
    notify_user(
        user=report.patient, type='report',
        title='Your medical report is ready 📋',
        message=(
            f'Dr. {report.doctor.user.full_name} at {report.clinic.name} '
            f'has shared your medical report.\n\n'
            f'Diagnosis: {report.diagnosis[:150]}'
        ),
        link='/appointments/my/reports/',
        email_subject=f'[MediQueue] Medical report ready — {report.clinic.name}',
        email_template='emails/report_ready.html',
        email_context={
            'patient_name': report.patient.full_name,
            'doctor_name':  report.doctor.user.full_name,
            'clinic_name':  report.clinic.name,
            'diagnosis':    report.diagnosis[:200],
        }
    )


def notify_payment_submitted(appt):
    if appt.receptionist:
        notify_user(
            user=appt.receptionist, type='payment',
            title='Payment submitted — needs verification',
            message=(
                f'{appt.patient.full_name} submitted a payment of '
                f'{appt.booking_fee_currency} {appt.booking_fee} for their appointment. '
                f'Please verify it in the Payment Queue.'
            ),
            link='/finance/receptionist/payments/',
            email_subject=f'[MediQueue] Payment submitted by {appt.patient.full_name}',
            email_template='emails/payment_submitted.html',
            email_context={
                'patient_name': appt.patient.full_name,
                'clinic_name':  appt.clinic.name,
                'amount':       str(appt.booking_fee),
                'currency':     appt.booking_fee_currency,
            }
        )