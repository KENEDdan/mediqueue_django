from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.db.models import Q
from .models import User 
from .forms import (PatientLoginForm, StaffLoginForm, PatientRegisterForm,
                    ForgotPasswordStep1Form, SecurityAnswerForm, ResetPasswordForm)


# ── Landing ───────────────────────────────────────────────────

def landing(request):
    from apps.clinics.models import Clinic
    from apps.doctors.models import Doctor
    from apps.appointments.models import Appointment

    # Search
    q = request.GET.get('q', '').strip()
    clinics_qs = Clinic.objects.filter(
        approval_status='approved', is_active=True,
        subscription_status__in=['trial','active']
    ).order_by('name')
    if q:
        clinics_qs = clinics_qs.filter(name__icontains=q)

    stats = {
        'clinics':      Clinic.objects.filter(approval_status='approved', is_active=True).count(),
        'doctors':      Doctor.objects.filter(user__is_active=True).count(),
        'patients':     User.objects.filter(role='patient').count(),
        'appointments': Appointment.objects.count(),
    }
    stats_list = [
        ('🏥', stats['clinics'],      'Clinics & Hospitals', '#1A7A9E'),
        ('👨‍⚕️', stats['doctors'],    'Registered Doctors',  '#E05C2A'),
        ('🧑',  stats['patients'],    'Patients Served',     '#2D9E6B'),
        ('📅',  stats['appointments'],'Appointments Booked', '#E8A020'),
    ]
    steps = [
        ('1','🔍','Browse Clinics','Search clinics and hospitals and see what they specialise in'),
        ('2','📝','Describe Your Condition','Tell us what you are experiencing when requesting'),
        ('3','✅','Get Confirmed','A receptionist reviews your request and assigns the right doctor'),
    ]
    return render(request, 'landing/index.html', {
        'stats':      stats,
        'stats_list': stats_list,
        'steps':      steps,
        'clinics':    clinics_qs[:12],
        'plans':      settings.SUBSCRIPTION_PLANS,
    })


# ── Dashboard router ──────────────────────────────────────────

@login_required
def dashboard(request):
    role = request.user.role
    routes = {
        'super_admin':  'superadmin:dashboard',
        'clinic_admin': 'clinic_admin_dashboard',
        'receptionist': 'receptionist_dashboard',
        'doctor':       'doctor_dashboard',
        'patient':      'patient_dashboard',
    }
    return redirect(routes.get(role, 'landing'))


# ── Patient Login ─────────────────────────────────────────────

def patient_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = PatientLoginForm(data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        if user.role != 'patient':
            messages.error(request, 'This login is for patients only. Staff use the Staff Login button.')
            return render(request, 'accounts/patient_login.html', {'form': form})
        login(request, user)
        next_url = request.GET.get('next', 'patient_dashboard')
        return redirect(next_url)
    return render(request, 'accounts/patient_login.html', {'form': form})


# ── Staff Login ───────────────────────────────────────────────

def staff_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = StaffLoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email    = form.cleaned_data['email'].strip().lower()
        password = form.cleaned_data['password']
        user = authenticate(request, username=email, password=password)
        if not user:
            messages.error(request, 'Invalid email or password.')
            return render(request, 'accounts/staff_login.html', {'form': form})
        if user.role == 'patient':
            messages.error(request, 'Patients use the Patient Login button.')
            return render(request, 'accounts/staff_login.html', {'form': form})
        if user.clinic:
            if user.clinic.approval_status == 'pending':
                messages.warning(request,
                    'Your clinic registration is under review. '
                    'You will receive an email once approved.')
                return render(request, 'accounts/staff_login.html', {'form': form})
            if user.clinic.approval_status == 'rejected':
                messages.error(request,
                    'Your clinic registration was not approved. '
                    'Check your email for details.')
                return render(request, 'accounts/staff_login.html', {'form': form})

        # ── 2FA for clinic_admin ──────────────────────────
        if user.role == 'clinic_admin':
            request.session['pending_2fa_user_id'] = user.pk
            return redirect('verify_2fa')

        login(request, user)
        from apps.security.audit import log_login_success
        log_login_success(user, request.META.get('REMOTE_ADDR',''), 
                         request.META.get('HTTP_USER_AGENT',''))
        return redirect('dashboard')
    return render(request, 'accounts/staff_login.html', {'form': form})

# ── Patient Register ──────────────────────────────────────────

def register_patient(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    form = PatientRegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='apps.accounts.backends.MediQueueAuthBackend')
        messages.success(request, f'Welcome to MediQueue, {user.first_name}! Your account is ready.')
        return redirect('patient_dashboard')
    return render(request, 'accounts/register_patient.html', {'form': form})


# ── Forgot Password ───────────────────────────────────────────

def forgot_password(request):
    # Step stored in session: step1 → step2 → step3
    step = request.session.get('reset_step', 'step1')

    if request.method == 'POST':
        if step == 'step1':
            form = ForgotPasswordStep1Form(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email'].strip().lower()
                try:
                    user = User.objects.get(Q(email=email) | Q(generated_email=email))
                    if not user.security_question:
                        messages.error(request, 'No security question set. Contact your admin.')
                    else:
                        request.session['reset_email']    = email
                        request.session['reset_question'] = user.security_question
                        request.session['reset_step']     = 'step2'
                        return redirect('forgot_password')
                except User.DoesNotExist:
                    messages.error(request, 'No account found with this email.')
            return render(request, 'accounts/forgot_password.html',
                          {'form': form, 'step': 'step1'})

        elif step == 'step2':
            form = SecurityAnswerForm(request.POST)
            if form.is_valid():
                answer = form.cleaned_data['answer'].strip().lower()
                email  = request.session.get('reset_email', '')
                try:
                    user = User.objects.get(Q(email=email) | Q(generated_email=email))
                    if user.security_answer.lower() == answer:
                        request.session['reset_user_id'] = user.pk
                        request.session['reset_step']    = 'step3'
                        return redirect('forgot_password')
                    else:
                        messages.error(request, 'Incorrect answer.')
                except User.DoesNotExist:
                    messages.error(request, 'Session expired. Start again.')
                    request.session['reset_step'] = 'step1'
            return render(request, 'accounts/forgot_password.html', {
                'form':     form,
                'step':     'step2',
                'question': request.session.get('reset_question', ''),
            })

        elif step == 'step3':
            form = ResetPasswordForm(request.POST)
            if form.is_valid():
                user_id = request.session.get('reset_user_id')
                try:
                    user = User.objects.get(pk=user_id)
                    user.set_password(form.cleaned_data['password'])
                    user.save()
                    # Clear session
                    for k in ['reset_step','reset_email','reset_question','reset_user_id']:
                        request.session.pop(k, None)
                    messages.success(request, 'Password reset successfully. Please sign in.')
                    return redirect('staff_login')
                except User.DoesNotExist:
                    messages.error(request, 'Session expired. Start again.')
                    request.session['reset_step'] = 'step1'
            return render(request, 'accounts/forgot_password.html',
                          {'form': form, 'step': 'step3'})

    # GET
    forms_by_step = {
        'step1': ForgotPasswordStep1Form(),
        'step2': SecurityAnswerForm(),
        'step3': ResetPasswordForm(),
    }
    return render(request, 'accounts/forgot_password.html', {
        'form':     forms_by_step.get(step, ForgotPasswordStep1Form()),
        'step':     step,
        'question': request.session.get('reset_question', ''),
    })


# ── Logout ────────────────────────────────────────────────────

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been signed out.')
    return redirect('landing')


# ── Error handlers ────────────────────────────────────────────

def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)

def error_500(request):
    return render(request, 'errors/500.html', status=500)

# In accounts/views.py
def verify_2fa(request):
    from utils.two_factor import generate_otp, send_otp_email, verify_otp
    user_id = request.session.get('pending_2fa_user_id')
    if not user_id:
        return redirect('staff_login')

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect('staff_login')

    if request.method == 'GET':
        # Generate and send OTP
        code = generate_otp(user.email)
        send_otp_email(user.email, user.full_name, code)
        request.session['otp_attempts'] = 0

    if request.method == 'POST':
        code     = request.POST.get('code', '').strip()
        attempts = request.session.get('otp_attempts', 0)

        if attempts >= 3:
            del request.session['pending_2fa_user_id']
            messages.error(request, 'Too many incorrect attempts. Please sign in again.')
            return redirect('staff_login')

        ok, reason = verify_otp(user.email, code)
        if ok:
            del request.session['pending_2fa_user_id']
            login(request, user, backend='apps.accounts.backends.MediQueueAuthBackend')
            return redirect('dashboard')
        else:
            request.session['otp_attempts'] = attempts + 1
            messages.error(request, f'{reason} — {2 - attempts} attempt(s) remaining.')

    return render(request, 'accounts/verify_2fa.html', {'user': user})

import secrets
from django.utils import timezone
from datetime import timedelta

def send_verification_email(user, request):
    """Send email verification link after registration."""
    token = secrets.token_urlsafe(32)
    user.email_verify_token  = token
    user.email_token_expires = timezone.now() + timedelta(hours=24)
    user.save(update_fields=['email_verify_token', 'email_token_expires'])

    verify_url = request.build_absolute_uri(
        f'/verify-email/{token}/'
    )
    from apps.notifications.utils import send_email
    from django.conf import settings
    send_email(
        to=user.email,
        subject='[MediQueue] Verify your email address',
        template='emails/verify_email.html',
        context={
            'name':       user.full_name,
            'verify_url': verify_url,
            'app_name':   settings.APP_NAME,
        }
    )


def verify_email(request, token):
    try:
        user = User.objects.get(email_verify_token=token)
        if user.email_token_expires < timezone.now():
            messages.error(request, 'Verification link expired. Please register again.')
            return redirect('register_patient')
        user.email_verified     = True
        user.email_verify_token = ''
        user.save(update_fields=['email_verified', 'email_verify_token'])
        login(request, user, backend='apps.accounts.backends.MediQueueAuthBackend')
        messages.success(request, '✅ Email verified! Welcome to MediQueue.')
        return redirect('patient_dashboard')
    except User.DoesNotExist:
        messages.error(request, 'Invalid verification link.')
        return redirect('landing')
    
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    """Health check endpoint for load balancers and uptime monitors."""
    checks = {}
    overall = 'healthy'

    # Database
    try:
        connection.ensure_connection()
        checks['database'] = 'ok'
    except Exception as e:
        checks['database'] = f'error: {str(e)[:50]}'
        overall = 'degraded'

    # Cache (Redis)
    try:
        from django.core.cache import cache
        cache.set('health_check', '1', 10)
        cache.get('health_check')
        checks['cache'] = 'ok'
    except Exception as e:
        checks['cache'] = f'error: {str(e)[:50]}'
        overall = 'degraded'

    return JsonResponse({
        'status':  overall,
        'checks':  checks,
        'version': '1.0.0',
    }, status=200 if overall == 'healthy' else 503)

@login_required
def export_my_data(request):
    """Patient downloads all their data as JSON (GDPR right to portability)."""
    if request.user.role != 'patient':
        return redirect('dashboard')

    import json
    from django.http import HttpResponse
    from apps.appointments.models import Appointment
    from apps.records.models import MedicalReport

    appts = list(Appointment.objects.filter(patient=request.user).values(
        'id','clinic__name','condition_description','preferred_date',
        'status','confirmed_date','confirmed_time_slot','requested_at'
    ))
    reports = list(MedicalReport.objects.filter(
        patient=request.user, is_shared_with_patient=True
    ).values(
        'id','clinic__name','doctor__user__full_name',
        'chief_complaint','diagnosis','prescriptions',
        'treatment_plan','follow_up_date','created_at'
    ))

    data = {
        'exported_at': str(timezone.now()),
        'patient': {
            'full_name':     request.user.full_name,
            'email':         request.user.email,
            'phone':         request.user.phone,
            'gender':        request.user.gender,
            'date_of_birth': str(request.user.date_of_birth) if request.user.date_of_birth else None,
            'address':       request.user.address,
            'created_at':    str(request.user.created_at),
        },
        'appointments':    appts,
        'medical_reports': reports,
    }

    response = HttpResponse(
        json.dumps(data, indent=2, default=str),
        content_type='application/json'
    )
    response['Content-Disposition'] = 'attachment; filename="my-mediqueue-data.json"'
    return response


@login_required
def request_account_deletion(request):
    """Patient requests account deletion (GDPR right to erasure)."""
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        # Anonymize instead of delete (to preserve medical history integrity)
        user = request.user
        user.full_name    = f'Deleted User #{user.pk}'
        user.email        = f'deleted_{user.pk}@deleted.invalid'
        user.phone        = ''
        user.address      = ''
        user.is_active    = False
        user.set_unusable_password()
        user.save()
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, 'Your account has been deleted. We are sorry to see you go.')
        return redirect('landing')
    return render(request, 'accounts/delete_account.html')