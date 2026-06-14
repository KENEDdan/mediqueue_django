from celery import shared_task
from datetime import date, timedelta
from django.conf import settings


@shared_task
def check_expiring_subscriptions():
    """
    Run daily. Warns clinics 7 days before expiry,
    suspends on expiry day, allows 3-day grace period.
    """
    from apps.clinics.models import Clinic
    from apps.notifications.utils import send_email

    today = date.today()

    # 7-day warning
    warning_date = today + timedelta(days=7)
    expiring_soon = Clinic.objects.filter(
        subscription_status='active',
        subscription_expiry=warning_date
    ).select_related()

    for clinic in expiring_soon:
        admin = clinic.staff.filter(role='clinic_admin').first()
        if admin:
            send_email(
                to=admin.email,
                subject=f'[MediQueue] Your subscription expires in 7 days',
                template='emails/subscription_expiring.html',
                context={
                    'clinic_name':   clinic.name,
                    'admin_name':    admin.full_name,
                    'expiry_date':   str(clinic.subscription_expiry),
                    'plan':          clinic.get_subscription_plan_display(),
                    'app_name':      settings.APP_NAME,
                }
            )

    # Grace period (3 days after expiry — still active)
    grace_expiry = today - timedelta(days=3)
    past_grace = Clinic.objects.filter(
        subscription_status='active',
        subscription_expiry__lt=grace_expiry
    )
    for clinic in past_grace:
        clinic.subscription_status = 'expired'
        clinic.is_active = False
        clinic.save(update_fields=['subscription_status', 'is_active'])
        admin = clinic.staff.filter(role='clinic_admin').first()
        if admin:
            send_email(
                to=admin.email,
                subject=f'[MediQueue] Your subscription has expired',
                template='emails/subscription_expired.html',
                context={
                    'clinic_name': clinic.name,
                    'admin_name':  admin.full_name,
                    'app_name':    settings.APP_NAME,
                }
            )

    # Trial ending in 3 days
    trial_ending = today + timedelta(days=3)
    trials = Clinic.objects.filter(
        subscription_status='trial',
        subscription_expiry=trial_ending
    )
    for clinic in trials:
        admin = clinic.staff.filter(role='clinic_admin').first()
        if admin:
            send_email(
                to=admin.email,
                subject=f'[MediQueue] Your free trial ends in 3 days',
                template='emails/trial_ending.html',
                context={
                    'clinic_name': clinic.name,
                    'admin_name':  admin.full_name,
                    'expiry_date': str(clinic.subscription_expiry),
                    'app_name':    settings.APP_NAME,
                }
            )


@shared_task
def generate_monthly_summary():
    """Run on 1st of each month. Builds revenue snapshot."""
    from apps.finance.models import PlatformFinanceSummary, PlatformSubscriptionPayment
    from apps.clinics.models import Clinic
    from django.db.models import Sum, Count
    from decimal import Decimal

    last_month_end   = date.today().replace(day=1) - timedelta(days=1)
    last_month_start = last_month_end.replace(day=1)

    payments = PlatformSubscriptionPayment.objects.filter(
        status='paid',
        paid_at__date__gte=last_month_start,
        paid_at__date__lte=last_month_end
    )

    totals = {
        'total_revenue':    payments.aggregate(t=Sum('amount'))['t'] or Decimal('0'),
        'total_subscriptions': payments.count(),
        'starter_revenue':  payments.filter(plan='starter').aggregate(t=Sum('amount'))['t'] or Decimal('0'),
        'growth_revenue':   payments.filter(plan='growth').aggregate(t=Sum('amount'))['t'] or Decimal('0'),
        'enterprise_revenue':payments.filter(plan='enterprise').aggregate(t=Sum('amount'))['t'] or Decimal('0'),
        'new_clinics':      Clinic.objects.filter(created_at__date__gte=last_month_start,
                                                   created_at__date__lte=last_month_end).count(),
    }

    PlatformFinanceSummary.objects.update_or_create(
        month=last_month_start,
        defaults=totals
    )


@shared_task
def send_appointment_reminder():
    """Run every morning at 8AM. Reminds patients of appointments tomorrow."""
    from apps.appointments.models import Appointment
    from apps.notifications.utils import send_email

    tomorrow = date.today() + timedelta(days=1)
    appts = Appointment.objects.filter(
        confirmed_date=tomorrow,
        status='confirmed'
    ).select_related('patient', 'clinic', 'doctor__user')

    for appt in appts:
        send_email(
            to=appt.patient.email,
            subject=f'[MediQueue] Reminder: Appointment tomorrow at {appt.clinic.name}',
            template='emails/appointment_reminder.html',
            context={
                'patient_name':  appt.patient.full_name,
                'clinic_name':   appt.clinic.name,
                'doctor_name':   appt.doctor.user.full_name if appt.doctor else 'Your doctor',
                'date':          str(appt.confirmed_date),
                'time':          str(appt.confirmed_time_slot),
                'app_name':      settings.APP_NAME,
            }
        )