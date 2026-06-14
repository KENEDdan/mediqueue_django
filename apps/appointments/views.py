from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Appointment, AppointmentPayment
from apps.clinics.models import Clinic
from apps.doctors.models import Doctor, DoctorBlockedDate, DoctorSchedule
from apps.finance.models import ClinicTransaction, PlatformCommission


# ── Helpers ────────────────────────────────────────────────────

def _require_receptionist(view_func):
    """Decorator: allow only receptionists and clinic admins."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or \
                request.user.role not in ('receptionist', 'clinic_admin'):
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_available_slots(doctor, target_date_str):
    """Return a list of HH:MM strings for open slots on target_date_str."""
    try:
        target = date.fromisoformat(target_date_str)
    except (ValueError, TypeError):
        return []

    day_of_week = target.weekday()
    try:
        schedule = DoctorSchedule.objects.get(
            doctor=doctor, day_of_week=day_of_week, is_active=True
        )
    except DoctorSchedule.DoesNotExist:
        return []

    if DoctorBlockedDate.objects.filter(doctor=doctor, blocked_date=target).exists():
        return []

    start    = datetime.combine(target, schedule.start_time)
    end      = datetime.combine(target, schedule.end_time)
    duration = timedelta(minutes=doctor.slot_duration_mins)

    booked = set(
        str(t)[:5]
        for t in Appointment.objects.filter(
            doctor=doctor,
            confirmed_date=target,
            status__in=('confirmed', 'completed'),
        ).values_list('confirmed_time_slot', flat=True)
    )

    slots, current = [], start
    while current + duration <= end:
        slot_str = current.strftime('%H:%M')
        if slot_str not in booked:
            slots.append(slot_str)
        current += duration
    return slots


# ── Patient views ──────────────────────────────────────────────

@login_required
def patient_dashboard(request):
    if request.user.role != 'patient':
        return redirect('dashboard')

    appts = (
        Appointment.objects
        .filter(patient=request.user)
        .select_related('clinic', 'doctor__user', 'doctor__specialization', 'payment')
        .order_by('-requested_at')
    )

    counts = {
        s: 0 for s in [
            'pending', 'proposed', 'accepted', 'awaiting_payment',
            'payment_submitted', 'confirmed', 'completed', 'cancelled',
        ]
    }
    for a in appts:
        if a.status in counts:
            counts[a.status] += 1

    return render(request, 'patient/dashboard.html', {
        'appts': appts,
        'counts': counts,
    })


@login_required
def book_appointment(request):
    if request.user.role != 'patient':
        return redirect('dashboard')

    from apps.clinics.models import Specialization

    clinic_id = request.GET.get('clinic') or request.POST.get('clinic_id')
    spec_id   = request.GET.get('spec')

    clinics = Clinic.objects.filter(
        approval_status='approved',
        is_active=True,
        subscription_status__in=['trial', 'active'],
    ).order_by('name')
    specializations = Specialization.objects.all().order_by('name')

    pre_clinic = None
    if clinic_id:
        try:
            pre_clinic = Clinic.objects.get(pk=clinic_id, approval_status='approved')
        except Clinic.DoesNotExist:
            pass

    if request.method == 'POST':
        cid             = request.POST.get('clinic_id')
        pref_date       = request.POST.get('preferred_date')
        pref_time       = request.POST.get('preferred_time_of_day', 'Morning')
        condition       = request.POST.get('condition', '').strip()
        spec_preference = request.POST.get('specialization_preference', '').strip()
        understand_spec = request.POST.get('understand_specialization', 'no')

        if not all([cid, pref_date, condition]):
            messages.error(
                request,
                'Please fill in all required fields — clinic, date, and your symptoms.',
            )
            return redirect(request.path)

        try:
            clinic = Clinic.objects.get(
                pk=cid, approval_status='approved', is_active=True
            )
        except Clinic.DoesNotExist:
            messages.error(request, 'Invalid clinic selected.')
            return redirect(request.path)

        # Optionally prepend specialization preference to the condition description.
        full_condition = condition
        if spec_preference and understand_spec == 'yes':
            try:
                spec = Specialization.objects.get(pk=spec_preference)
                full_condition = f'[Specialization preference: {spec.name}]\n\n{condition}'
            except Specialization.DoesNotExist:
                pass

        appt = Appointment.objects.create(
            clinic                = clinic,
            patient               = request.user,
            condition_description = full_condition,
            preferred_date        = pref_date,
            preferred_time_of_day = pref_time,
            clinic_name_snapshot  = clinic.name,
            status                = 'pending',
        )

        try:
            from apps.notifications.utils import notify_appointment_received
            notify_appointment_received(appt)
        except Exception as e:
            print(f'[Email] {e}')

        messages.success(
            request,
            f'✅ Request submitted to <strong>{clinic.name}</strong>. '
            f'A receptionist will review and propose a time slot shortly.',
        )
        return redirect('patient_dashboard')

    return render(request, 'patient/book.html', {
        'clinics':         clinics,
        'pre_clinic':      pre_clinic,
        'specializations': specializations,
        'pre_spec':        spec_id,
    })


@login_required
def patient_respond_proposal(request, appt_id):
    """Patient accepts or declines the receptionist's proposed slot."""
    appt = get_object_or_404(
        Appointment, pk=appt_id, patient=request.user, status='proposed'
    )

    if request.method == 'POST':
        response = request.POST.get('response')

        if response == 'accept':
            appt.patient_response    = 'accepted'
            appt.patient_response_at = timezone.now()
            appt.confirmed_date      = appt.proposed_date
            appt.confirmed_time_slot = appt.proposed_time_slot
            appt.status              = 'awaiting_payment'
            appt.save()
            messages.success(
                request,
                f'✅ Slot accepted! Please pay the booking fee of '
                f'<strong>{appt.booking_fee_currency} {appt.booking_fee}</strong> to confirm.',
            )
            return redirect('patient_pay_booking', appt_id=appt.pk)

        elif response == 'decline':
            appt.patient_response    = 'declined'
            appt.patient_response_at = timezone.now()
            appt.status              = 'pending'
            appt.save()
            messages.warning(
                request,
                'Slot declined. The receptionist will be notified to propose a new time.',
            )
            return redirect('patient_dashboard')

    return render(request, 'appointments/patient_proposal.html', {'appt': appt})


@login_required
def patient_pay_booking(request, appt_id):
    """Patient submits payment / proof of payment for the booking fee."""
    appt = get_object_or_404(
        Appointment,
        pk=appt_id,
        patient=request.user,
        status__in=['awaiting_payment', 'payment_submitted'],
    )
    existing_payment = getattr(appt, 'payment', None)

    if request.method == 'POST':
        method    = request.POST.get('method')
        reference = request.POST.get('reference', '').strip()
        proof     = request.FILES.get('proof_of_payment')

        if not method:
            messages.error(request, 'Please select a payment method.')
            return redirect(request.path)

        if existing_payment:
            existing_payment.method    = method
            existing_payment.reference = reference
            if proof:
                existing_payment.proof_of_payment = proof
            existing_payment.status  = 'pending'
            existing_payment.paid_at = timezone.now()
            existing_payment.save()
        else:
            AppointmentPayment.objects.create(
                appointment      = appt,
                amount           = appt.booking_fee,
                currency         = appt.booking_fee_currency,
                method           = method,
                reference        = reference,
                proof_of_payment = proof,
                status           = 'pending',
                paid_at          = timezone.now(),
            )

        appt.status = 'payment_submitted'
        appt.save()

        try:
            from apps.notifications.utils import notify_payment_submitted
            notify_payment_submitted(appt)
        except Exception as e:
            print(f'[Email] {e}')

        messages.success(
            request,
            '✅ Payment submitted! The receptionist will verify and confirm your appointment.',
        )
        return redirect('patient_dashboard')

    return render(request, 'appointments/payment.html', {
        'appt': appt,
        'existing': existing_payment,
    })


@login_required
def patient_cancel_appointment(request, appt_id):
    """Patient can cancel pending, proposed, or awaiting-payment appointments."""
    appt = get_object_or_404(
        Appointment,
        pk=appt_id,
        patient=request.user,
        status__in=['pending', 'proposed', 'awaiting_payment'],
    )

    if request.method == 'POST':
        reason = request.POST.get('reason', 'Cancelled by patient').strip()
        appt.status         = 'cancelled'
        appt.rejection_note = f'Cancelled by patient: {reason}'
        appt.save()
        messages.success(request, 'Appointment cancelled.')
        return redirect('patient_dashboard')

    return render(request, 'appointments/patient_cancel.html', {'appt': appt})


@login_required
def patient_reports(request):
    """Patient views all their shared medical reports."""
    if request.user.role != 'patient':
        return redirect('dashboard')

    from apps.records.models import MedicalReport

    reports = (
        MedicalReport.objects
        .filter(patient=request.user, is_shared_with_patient=True)
        .select_related('doctor__user', 'clinic', 'appointment')
        .order_by('-created_at')
    )
    return render(request, 'patient/reports.html', {'reports': reports})


# ── Receptionist views ─────────────────────────────────────────

@login_required
@_require_receptionist
def receptionist_dashboard(request):
    clinic = request.user.clinic

    pending_count   = Appointment.objects.filter(clinic=clinic, status='pending').count()
    proposed_count  = Appointment.objects.filter(clinic=clinic, status='proposed').count()
    payment_count   = Appointment.objects.filter(clinic=clinic, status='payment_submitted').count()
    confirmed_count = Appointment.objects.filter(clinic=clinic, status='confirmed').count()

    today_appts = (
        Appointment.objects
        .filter(clinic=clinic, confirmed_date=date.today(), status='confirmed')
        .select_related('patient', 'doctor__user')
        .order_by('confirmed_time_slot')
    )
    recent_pending = (
        Appointment.objects
        .filter(clinic=clinic, status='pending')
        .select_related('patient')
        .order_by('requested_at')[:5]
    )

    return render(request, 'receptionist/dashboard.html', {
        'clinic':          clinic,
        'pending_count':   pending_count,
        'proposed_count':  proposed_count,
        'payment_count':   payment_count,
        'confirmed_count': confirmed_count,
        'today_appts':     today_appts,
        'recent_pending':  recent_pending,
    })


@login_required
@_require_receptionist
def pending_appointments(request):
    clinic = request.user.clinic
    appts = (
        Appointment.objects
        .filter(clinic=clinic, status='pending')
        .select_related('patient')
        .order_by('requested_at')
    )
    return render(request, 'receptionist/pending.html', {
        'clinic': clinic,
        'appts':  appts,
    })


@login_required
@_require_receptionist
def propose_appointment(request, appt_id):
    """Receptionist proposes a doctor, time slot, and booking fee to the patient."""
    clinic  = request.user.clinic
    appt    = get_object_or_404(
        Appointment, pk=appt_id, clinic=clinic, status__in=['pending', 'proposed']
    )
    doctors = (
        Doctor.objects
        .filter(clinic=clinic, user__is_active=True, is_accepting_patients=True)
        .select_related('user', 'specialization')
    )

    if request.method == 'POST':
        doctor_id     = request.POST.get('doctor')
        prop_date     = request.POST.get('proposed_date')
        prop_slot     = request.POST.get('time_slot')
        prop_message  = request.POST.get('proposal_message', '').strip()
        booking_fee   = request.POST.get('booking_fee', '0')

        if not all([doctor_id, prop_date, prop_slot]):
            messages.error(request, 'Doctor, date and time slot are all required.')
            return redirect(request.path)

        try:
            doctor      = Doctor.objects.get(pk=doctor_id, clinic=clinic)
            booking_fee = float(booking_fee)
        except (Doctor.DoesNotExist, ValueError):
            messages.error(request, 'Invalid doctor or booking fee.')
            return redirect(request.path)

        appt.doctor             = doctor
        appt.proposed_date      = prop_date
        appt.proposed_time_slot = prop_slot
        appt.proposal_message   = prop_message
        appt.booking_fee        = booking_fee
        appt.proposal_sent_at   = timezone.now()
        appt.receptionist       = request.user
        appt.status             = 'proposed'
        appt.reviewed_at        = timezone.now()
        appt.save()

        try:
            from apps.notifications.utils import notify_slot_proposed
            notify_slot_proposed(appt)
        except Exception as e:
            print(f'[Email] {e}')

        messages.success(
            request,
            f'✅ Slot proposed to {appt.patient.full_name}. '
            f'Waiting for their confirmation.',
        )
        return redirect('pending_appointments')

    return render(request, 'appointments/proposal.html', {
        'clinic':  clinic,
        'appt':    appt,
        'doctors': doctors,
    })


@login_required
@_require_receptionist
def payment_queue(request):
    """Payments submitted by patients that are waiting for verification."""
    clinic = request.user.clinic
    appts  = (
        Appointment.objects
        .filter(clinic=clinic, status='payment_submitted')
        .select_related('patient', 'doctor__user', 'payment')
        .order_by('payment__paid_at')
    )
    return render(request, 'receptionist/payment_queue.html', {
        'clinic': clinic,
        'appts':  appts,
    })


@login_required
@_require_receptionist
def verify_payment(request, appt_id):
    """Receptionist verifies payment and fully confirms the appointment."""
    clinic  = request.user.clinic
    appt    = get_object_or_404(
        Appointment, pk=appt_id, clinic=clinic, status='payment_submitted'
    )
    payment = get_object_or_404(AppointmentPayment, appointment=appt)

    if request.method == 'POST':
        action = request.POST.get('action')
        notes  = request.POST.get('notes', '').strip()

        if action == 'verify':
            gross      = appt.booking_fee
            rate       = Decimal(str(settings.PLATFORM_COMMISSION_RATE)) / 100
            commission = (gross * rate).quantize(Decimal('0.01'))
            net_clinic = gross - commission

            txn = ClinicTransaction.objects.create(
                clinic       = appt.clinic,
                appointment  = payment,
                patient      = appt.patient,
                amount       = gross,
                currency     = appt.booking_fee_currency,
                method       = payment.method,
                reference_no = payment.reference,
                status       = 'verified',
                verified_by  = request.user,
                verified_at  = timezone.now(),
                paid_at      = payment.paid_at,
            )
            PlatformCommission.objects.create(
                clinic            = appt.clinic,
                transaction       = txn,
                gross_amount      = gross,
                commission_rate   = settings.PLATFORM_COMMISSION_RATE,
                commission_amount = commission,
                net_to_clinic     = net_clinic,
            )

            payment.status      = 'verified'
            payment.verified_at = timezone.now()
            payment.verified_by = request.user
            payment.notes       = notes
            payment.save()

            appt.status = 'confirmed'
            appt.save()

            try:
                from apps.notifications.utils import notify_appointment_confirmed
                notify_appointment_confirmed(appt)
            except Exception as e:
                print(f'[Email] {e}')

            messages.success(
                request,
                f'✅ Payment verified! Appointment confirmed for '
                f'{appt.patient.full_name} on {appt.confirmed_date}.',
            )

        elif action == 'reject':
            payment.status = 'rejected'
            payment.notes  = notes
            payment.save()

            appt.status = 'awaiting_payment'
            appt.save()

            messages.warning(
                request,
                f'Payment rejected. {appt.patient.full_name} notified to resubmit.',
            )

        return redirect('payment_queue')

    return render(request, 'receptionist/verify_payment.html', {
        'clinic':  clinic,
        'appt':    appt,
        'payment': payment,
    })


@login_required
@_require_receptionist
def all_appointments(request):
    clinic = request.user.clinic
    status = request.GET.get('status', 'all')

    qs = (
        Appointment.objects
        .filter(clinic=clinic)
        .select_related('patient', 'doctor__user', 'receptionist', 'payment')
    )
    if status != 'all':
        qs = qs.filter(status=status)

    filter_options = [
        ('all',               'All'),
        ('pending',           'Pending'),
        ('proposed',          'Proposed'),
        ('awaiting_payment',  'Awaiting Payment'),
        ('payment_submitted', 'Payment Submitted'),
        ('confirmed',         'Confirmed'),
        ('completed',         'Completed'),
        ('cancelled',         'Cancelled'),
    ]

    return render(request, 'receptionist/all_appointments.html', {
        'clinic':         clinic,
        'appts':          qs.order_by('-requested_at'),
        'status':         status,
        'filter_options': filter_options,
    })


@login_required
@_require_receptionist
def reject_appointment(request, appt_id):
    clinic = request.user.clinic
    appt   = get_object_or_404(
        Appointment, pk=appt_id, clinic=clinic, status__in=['pending', 'proposed']
    )

    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a reason.')
            return redirect(request.path)

        appt.status         = 'cancelled'
        appt.rejection_note = reason
        appt.receptionist   = request.user
        appt.reviewed_at    = timezone.now()
        appt.save()

        try:
            from apps.notifications.utils import notify_appointment_cancelled
            notify_appointment_cancelled(appt)
        except Exception as e:
            print(f'[Email] {e}')

        messages.success(request, 'Appointment rejected.')
        return redirect('pending_appointments')

    return render(request, 'receptionist/reject.html', {
        'clinic': clinic,
        'appt':   appt,
    })


# ── API endpoints ──────────────────────────────────────────────

@login_required
def get_doctor_slots(request):
    """JSON endpoint: return available time slots for a doctor on a given date."""
    doctor_id = request.GET.get('doctor_id')
    date_str  = request.GET.get('date')
    try:
        doctor = Doctor.objects.get(pk=doctor_id)
        slots  = _get_available_slots(doctor, date_str)
        return JsonResponse({'slots': slots})
    except Doctor.DoesNotExist:
        return JsonResponse({'slots': []})