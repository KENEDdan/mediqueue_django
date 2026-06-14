from datetime import date, datetime, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Doctor, DoctorSchedule, DoctorBlockedDate
from apps.appointments.models import Appointment

DAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']


def _require_doctor(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'doctor':
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@_require_doctor
def doctor_dashboard(request):
    doctor     = get_object_or_404(Doctor, user=request.user)
    today      = date.today()
    today_appts = (Appointment.objects
                   .filter(doctor=doctor, confirmed_date=today,
                           status__in=['confirmed','completed','no_show'])
                   .select_related('patient').order_by('confirmed_time_slot'))
    stats = {
        'total':     Appointment.objects.filter(doctor=doctor).count(),
        'completed': Appointment.objects.filter(doctor=doctor, status='completed').count(),
        'upcoming':  Appointment.objects.filter(doctor=doctor, status='confirmed',
                                                 confirmed_date__gte=today).count(),
        'no_shows':  Appointment.objects.filter(doctor=doctor, status='no_show').count(),
    }
    schedules  = DoctorSchedule.objects.filter(doctor=doctor, is_active=True)
    sched_map  = {s.day_of_week: s for s in schedules}

    return render(request, 'doctor/dashboard.html', {
        'doctor': doctor, 'today': today, 'today_appts': today_appts,
        'stats': stats, 'sched_map': sched_map, 'days': DAYS,
    })


@login_required
@_require_doctor
def doctor_appointments(request):
    doctor = get_object_or_404(Doctor, user=request.user)
    filter_by = request.GET.get('filter', 'upcoming')
    today = date.today()

    qs = Appointment.objects.filter(doctor=doctor).select_related('patient')
    if filter_by == 'upcoming':
        qs = qs.filter(status='confirmed', confirmed_date__gte=today)
    elif filter_by == 'completed':
        qs = qs.filter(status='completed')
    elif filter_by == 'today':
        qs = qs.filter(confirmed_date=today)
    qs = qs.order_by('confirmed_date', 'confirmed_time_slot')

    return render(request, 'doctor/appointments.html', {
        'doctor': doctor, 'appointments': qs, 'filter_by': filter_by,
    })


@login_required
@_require_doctor
def mark_appointment(request, appt_id, new_status):
    doctor = get_object_or_404(Doctor, user=request.user)
    appt   = get_object_or_404(Appointment, pk=appt_id, doctor=doctor)
    if new_status in ('completed', 'no_show'):
        appt.status = new_status
        if new_status == 'completed':
            from django.utils import timezone
            appt.completed_at = timezone.now()
        appt.save()
        messages.success(request, f'Appointment marked as {new_status}.')
    return redirect('doctor_appointments')


@login_required
@_require_doctor
def save_doctor_note(request, appt_id):
    doctor = get_object_or_404(Doctor, user=request.user)
    appt   = get_object_or_404(Appointment, pk=appt_id, doctor=doctor)
    if request.method == 'POST':
        appt.doctor_note = request.POST.get('note', '').strip()
        appt.save(update_fields=['doctor_note'])
        messages.success(request, 'Note saved.')
    return redirect('doctor_appointments')


@login_required
@_require_doctor
def doctor_schedule(request):
    doctor    = get_object_or_404(Doctor, user=request.user)
    schedules_qs = DoctorSchedule.objects.filter(doctor=doctor)
    schedules = {s.day_of_week: s for s in schedules_qs}

    if request.method == 'POST':
        action = request.POST.get('action')
        day    = int(request.POST.get('day', 0))
        if action == 'set':
            start = request.POST.get('start_time')
            end   = request.POST.get('end_time')
            if start >= end:
                messages.error(request, 'End time must be after start time.')
                return redirect('doctor_schedule')
            DoctorSchedule.objects.update_or_create(
                doctor=doctor, day_of_week=day,
                defaults={'start_time': start, 'end_time': end, 'is_active': True}
            )
            messages.success(request, f'Schedule set for {DAYS[day]}.')
        elif action == 'remove':
            DoctorSchedule.objects.filter(doctor=doctor, day_of_week=day).update(is_active=False)
            messages.success(request, f'Schedule removed for {DAYS[day]}.')
        return redirect('doctor_schedule')

    times = [f'{h:02d}:{m:02d}' for h in range(6, 22) for m in (0, 30)]
    return render(request, 'doctor/schedule.html', {
        'doctor':    doctor,
        'schedules': schedules,
        'days':      list(enumerate(DAYS)),
        'times':     times,
        'today':     date.today(),
    })


@login_required
@_require_doctor
def doctor_blocked_dates(request):
    doctor  = get_object_or_404(Doctor, user=request.user)
    blocked = DoctorBlockedDate.objects.filter(doctor=doctor).order_by('blocked_date')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'block':
            d_str  = request.POST.get('date', '')
            reason = request.POST.get('reason', '').strip()
            try:
                d = date.fromisoformat(d_str)
                DoctorBlockedDate.objects.get_or_create(doctor=doctor, blocked_date=d,
                                                         defaults={'reason': reason})
                messages.success(request, f'{d_str} blocked.')
            except ValueError:
                messages.error(request, 'Invalid date format.')
        elif action == 'unblock':
            bd_id = request.POST.get('blocked_id')
            DoctorBlockedDate.objects.filter(pk=bd_id, doctor=doctor).delete()
            messages.success(request, 'Date unblocked.')
        return redirect('doctor_blocked_dates')

    return render(request, 'doctor/blocked_dates.html', {
        'doctor': doctor, 'blocked': blocked, 'today': date.today().isoformat(),
    })