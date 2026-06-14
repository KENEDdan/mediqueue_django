from datetime import date, timedelta
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone

from .models import (
    PlatformSubscriptionPayment, ClinicPayoutAccount,
    ClinicTransaction, PlatformFinanceSummary
)
from apps.appointments.models import AppointmentPayment


# ── Guards ────────────────────────────────────────────────────

def _super_admin_only(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'super_admin':
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _clinic_staff_only(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or \
                request.user.role not in ('clinic_admin', 'receptionist'):
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _clinic_admin_only(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'clinic_admin':
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── SUPERADMIN FINANCE DASHBOARD ──────────────────────────────

@login_required
@_super_admin_only
def superadmin_finance(request):
    # Date range filter
    period = request.GET.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30
    since = date.today() - timedelta(days=days)

    # Platform subscription revenue
    payments = PlatformSubscriptionPayment.objects.filter(
        status='paid', paid_at__date__gte=since
    )
    total_revenue    = payments.aggregate(t=Sum('amount'))['t'] or Decimal('0')
    total_paid_count = payments.count()

    # Revenue by plan
    revenue_by_plan = {}
    from django.conf import settings
    for pk in settings.SUBSCRIPTION_PLANS:
        rev = payments.filter(plan=pk).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        revenue_by_plan[pk] = {
            'name':    settings.SUBSCRIPTION_PLANS[pk]['name'],
            'icon':    settings.SUBSCRIPTION_PLANS[pk]['icon'],
            'revenue': rev,
            'count':   payments.filter(plan=pk).count(),
            # Add to superadmin_finance view context:
'filter_periods': [('7','7 days'),('30','30 days'),('90','90 days'),('365','1 year')],
        }

    # All subscription payments (paginated)
    all_payments = PlatformSubscriptionPayment.objects.select_related('clinic').order_by('-created_at')

    # Active subscriptions breakdown
    from apps.clinics.models import Clinic
    active_clinics    = Clinic.objects.filter(
        approval_status='approved', is_active=True,
        subscription_status__in=['trial', 'active']
    )
    trial_count       = active_clinics.filter(subscription_status='trial').count()
    active_paid_count = active_clinics.filter(subscription_status='active').count()
    expired_count     = Clinic.objects.filter(subscription_status='expired').count()

    # MRR estimate (Monthly Recurring Revenue)
    mrr = Decimal('0')
    for clinic in active_clinics.filter(subscription_status='active'):
        plan_info = settings.SUBSCRIPTION_PLANS.get(clinic.subscription_plan, {})
        if clinic.billing_cycle == 'annual':
            mrr += Decimal(str(plan_info.get('price_annual', 0))) / 12
        else:
            mrr += Decimal(str(plan_info.get('price_monthly', 0)))

    # Monthly revenue trend (last 6 months)
    monthly_trend = []
    for i in range(5, -1, -1):
        month_start = (date.today().replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        month_end   = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        rev = PlatformSubscriptionPayment.objects.filter(
            status='paid',
            paid_at__date__gte=month_start,
            paid_at__date__lte=month_end
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0')
        monthly_trend.append({
            'month': month_start.strftime('%b %Y'),
            'revenue': float(rev),
        })

    # Pending / failed
    pending_payments = PlatformSubscriptionPayment.objects.filter(
        status='pending').count()
    failed_payments  = PlatformSubscriptionPayment.objects.filter(
        status='failed', created_at__date__gte=since).count()

    # All clinic transactions (patient payments) visible to superadmin
    clinic_transactions = ClinicTransaction.objects.select_related(
        'clinic', 'patient'
    ).order_by('-paid_at')[:50]

    clinic_txn_total = ClinicTransaction.objects.filter(
        status='verified', paid_at__date__gte=since
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0')

    return render(request, 'finance/superadmin_finance.html', {
        'period':             period,
        'since':              since,
        'total_revenue':      total_revenue,
        'total_paid_count':   total_paid_count,
        'revenue_by_plan':    revenue_by_plan,
        'all_payments':       all_payments[:100],
        'trial_count':        trial_count,
        'active_paid_count':  active_paid_count,
        'expired_count':      expired_count,
        'mrr':                mrr,
        'monthly_trend':      monthly_trend,
        'pending_payments':   pending_payments,
        'failed_payments':    failed_payments,
        'clinic_transactions':clinic_transactions,
        'clinic_txn_total':   clinic_txn_total,
        'filter_periods': [
    ('7',   '7 days'),
    ('30',  '30 days'),
    ('90',  '90 days'),
    ('365', '1 year'),
],
    })



@login_required
@_super_admin_only
def record_subscription_payment(request):
    """Superadmin manually records a subscription payment (for non-Stripe payments)."""
    from apps.clinics.models import Clinic
    if request.method == 'POST':
        clinic_id = request.POST.get('clinic_id')
        amount    = request.POST.get('amount')
        plan      = request.POST.get('plan')
        billing   = request.POST.get('billing_cycle', 'monthly')
        method    = request.POST.get('method', 'manual_card')
        notes     = request.POST.get('notes', '')

        try:
            clinic = Clinic.objects.get(pk=clinic_id)
            amt    = Decimal(amount)
        except (Clinic.DoesNotExist, Exception):
            messages.error(request, 'Invalid clinic or amount.')
            return redirect('superadmin_finance')

        from datetime import timedelta
        duration   = 30 if billing == 'monthly' else 365
        period_end = date.today() + timedelta(days=duration)

        PlatformSubscriptionPayment.objects.create(
            clinic       = clinic,
            plan         = plan,
            billing_cycle= billing,
            amount       = amt,
            currency     = 'USD',
            method       = method,
            status       = 'paid',
            notes        = notes,
            period_start = date.today(),
            period_end   = period_end,
            paid_at      = timezone.now(),
        )

        # Activate clinic subscription
        clinic.subscription_plan   = plan
        clinic.billing_cycle       = billing
        clinic.subscription_status = 'active'
        clinic.subscription_expiry = period_end
        clinic.save()

        messages.success(request, f'✅ Payment recorded. {clinic.name} subscription activated.')
        return redirect('superadmin_finance')

    clinics = Clinic.objects.filter(approval_status='approved', is_active=True).order_by('name')
    from django.conf import settings
    return render(request, 'finance/record_payment.html', {
        'clinics': clinics,
        'plans':   settings.SUBSCRIPTION_PLANS,
    })


# ── CLINIC FINANCE DASHBOARD ──────────────────────────────────

@login_required
@_clinic_admin_only
def clinic_finance(request):
    clinic  = request.user.clinic
    period  = request.GET.get('period', '30')
    try:
        days = int(period)
    except ValueError:
        days = 30
    since = date.today() - timedelta(days=days)

    # Payout account
    payout_account = getattr(clinic, 'payout_account', None)

    # Transactions received from patients
    transactions = ClinicTransaction.objects.filter(clinic=clinic).order_by('-paid_at')
    period_txns  = transactions.filter(paid_at__date__gte=since)

    total_received  = period_txns.filter(status='verified').aggregate(
        t=Sum('amount'))['t'] or Decimal('0')
    pending_amount  = period_txns.filter(status='pending').aggregate(
        t=Sum('amount'))['t'] or Decimal('0')
    total_count     = period_txns.count()
    verified_count  = period_txns.filter(status='verified').count()

    # Revenue by payment method
    by_method = {}
    for txn in period_txns.filter(status='verified'):
        m = txn.method
        if m not in by_method:
            by_method[m] = Decimal('0')
        by_method[m] += txn.amount

    # Subscription payments made to platform
    sub_payments = PlatformSubscriptionPayment.objects.filter(clinic=clinic).order_by('-created_at')

    # Appointment payments queue (from AppointmentPayment)
    appt_payments = AppointmentPayment.objects.filter(
        appointment__clinic=clinic
    ).select_related('appointment__patient').order_by('-created_at')[:20]

    return render(request, 'finance/clinic_finance.html', {
        'clinic':          clinic,
        'period':          period,
        'since':           since,
        'payout_account':  payout_account,
        'transactions':    transactions[:100],
        'total_received':  total_received,
        'pending_amount':  pending_amount,
        'total_count':     total_count,
        'verified_count':  verified_count,
        'by_method':       by_method,
        'sub_payments':    sub_payments,
        'appt_payments':   appt_payments,
        'filter_periods': [
    ('7',   '7 days'),
    ('30',  '30 days'),
    ('90',  '90 days'),
    ('365', '1 year'),
],
    })


@login_required
@_clinic_admin_only
def setup_payout_account(request):
    """Clinic admin sets up their payout account."""
    clinic  = request.user.clinic
    account = getattr(clinic, 'payout_account', None)

    if request.method == 'POST':
        data = {
            'clinic':         clinic,
            'method':         request.POST.get('method'),
            'account_name':   request.POST.get('account_name', ''),
            'account_number': request.POST.get('account_number', ''),
            'bank_name':      request.POST.get('bank_name', ''),
            'bank_branch':    request.POST.get('bank_branch', ''),
            'swift_code':     request.POST.get('swift_code', ''),
            'paypal_email':   request.POST.get('paypal_email', ''),
            'instructions':   request.POST.get('instructions', ''),
            'booking_fee_default': request.POST.get('booking_fee_default') or 0,
            'currency':       request.POST.get('currency', 'USD'),
            'is_active':      True,
        }
        if account:
            for k, v in data.items():
                if k != 'clinic':
                    setattr(account, k, v)
            account.save()
        else:
            ClinicPayoutAccount.objects.create(**data)

        messages.success(request, '✅ Payout account updated. Patients will see these details when paying.')
        return redirect('clinic_finance')

    currencies = ['USD', 'KES', 'UGX', 'RWF', 'TZS', 'GHS', 'NGN', 'ZAR', 'XOF', 'EUR', 'GBP']
    return render(request, 'finance/payout_setup.html', {
        'clinic':      clinic,
        'account':     account,
        'methods':     ClinicPayoutAccount.METHOD_CHOICES,
        'currencies':  currencies,
    })


# ── RECEPTIONIST PAYMENT VIEW ──────────────────────────────────

@login_required
@_clinic_staff_only
def receptionist_payments(request):
    """Read-only view of recent patient payments for appointment scheduling."""
    clinic = request.user.clinic

    # Recent verified payments for context
    recent = ClinicTransaction.objects.filter(
        clinic=clinic, status='verified'
    ).select_related('patient').order_by('-paid_at')[:30]

    # Payment queue — submitted but not yet verified
    pending_queue = AppointmentPayment.objects.filter(
        appointment__clinic=clinic, status='pending'
    ).select_related('appointment__patient', 'appointment__doctor__user').order_by('-paid_at')

    # Payout account (so receptionist can share payment instructions)
    payout_account = getattr(clinic, 'payout_account', None)

    # Stats for today
    today_payments = ClinicTransaction.objects.filter(
        clinic=clinic, paid_at__date=date.today(), status='verified'
    ).aggregate(t=Sum('amount'), c=Count('id'))

    return render(request, 'finance/receptionist_payments.html', {
        'clinic':        clinic,
        'recent':        recent,
        'pending_queue': pending_queue,
        'payout_account':payout_account,
        'today_total':   today_payments['t'] or Decimal('0'),
        'today_count':   today_payments['c'] or 0,
    })

@login_required
def download_receipt(request, txn_id):
    """Generate and download a PDF receipt for a verified payment."""
    from apps.finance.models import ClinicTransaction
    txn = get_object_or_404(ClinicTransaction, reference=txn_id)

    # Only the patient or clinic staff can download
    if (hasattr(request.user, 'patient') or
            (request.user.clinic and request.user.clinic == txn.clinic)):
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import cm
        from django.http import HttpResponse
        import io

        buffer   = io.BytesIO()
        doc      = SimpleDocTemplate(buffer, pagesize=A4,
                                     leftMargin=2*cm, rightMargin=2*cm,
                                     topMargin=2*cm, bottomMargin=2*cm)
        styles   = getSampleStyleSheet()
        story    = []

        # Header
        title_style = ParagraphStyle('T', parent=styles['Title'],
                                     textColor=rl_colors.HexColor('#0B4F6C'))
        story.append(Paragraph('MediQueue — Payment Receipt', title_style))
        story.append(Spacer(1, 0.5*cm))

        # Receipt data
        data = [
            ['Receipt Reference', str(txn.reference)[:8].upper() + '...'],
            ['Clinic',            txn.clinic.name],
            ['Patient',           txn.patient_display],
            ['Amount',            f'{txn.currency} {txn.amount}'],
            ['Payment Method',    txn.method],
            ['Reference No.',     txn.reference_no or '—'],
            ['Status',            txn.status.upper()],
            ['Date',              txn.paid_at.strftime('%d %B %Y %H:%M')],
        ]
        t = Table(data, colWidths=[5*cm, 11*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),  (0,-1),  rl_colors.HexColor('#F0F4F8')),
            ('FONTNAME',      (0,0),  (0,-1),  'Helvetica-Bold'),
            ('GRID',          (0,0),  (-1,-1), 0.5, rl_colors.HexColor('#CED6DE')),
            ('TOPPADDING',    (0,0),  (-1,-1), 8),
            ('BOTTOMPADDING', (0,0),  (-1,-1), 8),
            ('LEFTPADDING',   (0,0),  (-1,-1), 12),
        ]))
        story.append(t)
        doc.build(story)

        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="receipt-{str(txn.reference)[:8]}.pdf"'
        return response

    messages.error(request, 'Access denied.')
    return redirect('patient_dashboard')