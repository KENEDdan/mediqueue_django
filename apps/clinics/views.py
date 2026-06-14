import re
from datetime import date, timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import Clinic, ClinicDocument, ClinicService, Specialization
from .forms  import ClinicRegisterForm, ClinicUpdateForm, ClinicServiceForm
from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.doctors.models import Doctor
from apps.notifications.utils import notify_user


# ── Helpers ────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    s = re.sub(r'[^a-z0-9]', '', text.lower().strip())
    return s[:20]


def _unique_slug(base: str) -> str:
    slug, counter = base, 2
    while Clinic.objects.filter(slug=slug).exists():
        slug = f'{base}{counter}'
        counter += 1
    return slug


def _detect_card_brand(number: str) -> str:
    n = number.replace(' ', '')
    if n.startswith('4'):                        return 'Visa'
    if n[:2] in [str(i) for i in range(51, 56)]: return 'Mastercard'
    if n[:2] in ('34', '37'):                    return 'Amex'
    return 'Card'


def _require_clinic_admin(view_func):
    """Decorator: must be logged in as clinic_admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'clinic_admin':
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Public views ───────────────────────────────────────────────

def clinic_detail(request, slug):
    clinic   = get_object_or_404(
        Clinic, slug=slug, approval_status='approved',
        is_active=True, deleted_at__isnull=True,
    )
    services = clinic.services.filter(is_active=True).select_related('specialization')
    doctors  = clinic.doctors.filter(user__is_active=True).select_related('user', 'specialization')
    return render(request, 'clinics/detail.html', {
        'clinic': clinic, 'services': services, 'doctors': doctors,
    })


def register_clinic(request):
    form = ClinicRegisterForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            slug = _unique_slug(_slugify(d['clinic_name']))

            # 1. Create clinic (pending approval)
            clinic = Clinic.objects.create(
                name                = d['clinic_name'].strip(),
                phone               = d['clinic_phone'],
                email               = d['clinic_email'],
                address             = d['clinic_address'],
                slug                = slug,
                subscription_plan   = d['subscription_plan'],
                billing_cycle       = d['billing_cycle'],
                approval_status     = 'pending',
                subscription_status = 'pending',
                card_last4          = d['card_number'][-4:],
                card_brand          = _detect_card_brand(d['card_number']),
                card_holder         = d['card_holder'],
            )

            # 2. Upload documents
            reg_cert = request.FILES.get('registration_cert')
            if reg_cert:
                ClinicDocument.objects.create(
                    clinic    = clinic,
                    doc_type  = 'registration_cert',
                    file_name = reg_cert.name,
                    file      = reg_cert,
                )
            medical_lic = request.FILES.get('medical_license')
            if medical_lic:
                ClinicDocument.objects.create(
                    clinic    = clinic,
                    doc_type  = 'license',
                    file_name = medical_lic.name,
                    file      = medical_lic,
                )

            # 3. Create clinic admin account
            admin_gen_email = User.generate_staff_email(d['admin_name'], slug)
            admin = User.objects.create_user(
                email             = d['admin_email'],
                full_name         = d['admin_name'],
                password          = d['admin_password'],
                clinic            = clinic,
                role              = 'clinic_admin',
                generated_email   = admin_gen_email,
                approval_status   = 'approved',
                registration_type = 'self_registered',
                security_question = d['security_question'],
                security_answer   = d['security_answer'].strip().lower(),
            )

            # 4. Notify all superadmins (in-app + email)
            superadmins = User.objects.filter(role='super_admin', is_active=True)
            for sa in superadmins:
                notify_user(
                    user=sa, type='approval',
                    title=f'New hospital registration: {clinic.name}',
                    message=(
                        f'{admin.full_name} has registered "{clinic.name}" '
                        f'and is requesting to join MediQueue.\n\n'
                        f'Plan selected: {clinic.get_subscription_plan_display()}\n'
                        f'Email: {admin.email}\n'
                        f'Phone: {clinic.phone}\n\n'
                        f'Please review their documents and approve or reject this application.'
                    ),
                    link='/superadmin/pending/',
                    email_subject=f'[MediQueue] New hospital application — {clinic.name}',
                    email_template='emails/generic_notification.html',
                    email_context={'link_url': 'https://mediqueue.health/superadmin/pending/'}
                )

            # 5. Notify the applicant (in-app + email) — confirmation of submission
            notify_user(
                user=admin, type='approval',
                title='Application Received — Under Review',
                message=(
                    f'Thank you for registering "{clinic.name}" on MediQueue.\n\n'
                    f'Your application is now under review by our team. '
                    f'We will verify your submitted documents and notify you '
                    f'once a decision has been made — usually within 24-48 hours.\n\n'
                    f'You can check your application status anytime by logging in.'
                ),
                link='/staff-login/',
                email_subject='[MediQueue] Your hospital application is under review',
                email_template='emails/generic_notification.html',
            )

        messages.success(
            request,
            f'✅ Registration submitted! Your hospital <strong>{clinic.name}</strong> is pending review. '
            f'Our team will verify your documents and notify you at {d["admin_email"]} '
            f'within 1–2 business days.',
        )
        return redirect('landing')

    return render(request, 'clinics/register.html', {
        'form':  form,
        'plans': settings.SUBSCRIPTION_PLANS,
    })

# ── Clinic admin views ─────────────────────────────────────────

@login_required
@_require_clinic_admin
def clinic_admin_dashboard(request):
    clinic = request.user.clinic

    stats = {
        'doctors':         clinic.doctors.filter(user__is_active=True).count(),
        'receptionists':   clinic.staff.filter(role='receptionist', is_active=True).count(),
        'patients':        Appointment.objects.filter(clinic=clinic).values('patient').distinct().count(),
        'pending_appts':   Appointment.objects.filter(clinic=clinic, status='pending').count(),
        'confirmed':       Appointment.objects.filter(clinic=clinic, status='confirmed').count(),
        'completed':       Appointment.objects.filter(clinic=clinic, status='completed').count(),
        'today':           Appointment.objects.filter(clinic=clinic, confirmed_date=date.today(), status='confirmed').count(),
        'pending_doctors': clinic.staff.filter(role='doctor', approval_status='pending').count(),
    }

    recent = (
        Appointment.objects
        .filter(clinic=clinic)
        .select_related('patient', 'doctor__user')
        .order_by('-requested_at')[:10]
    )

    plan_info        = settings.SUBSCRIPTION_PLANS.get(clinic.subscription_plan, {})
    max_doctors      = plan_info.get('max_doctors', 999)
    current_docs     = clinic.doctors.filter(user__is_active=True).count()
    doctor_usage_pct = (current_docs / max_doctors * 100) if max_doctors < 9999 else 0

    return render(request, 'clinic_admin/dashboard.html', {
        'clinic':             clinic,
        'stats':              stats,
        'recent':             recent,
        'plan':               plan_info,
        'doctor_usage_pct':   doctor_usage_pct,
        'max_doctors':        max_doctors,
        'current_docs':       current_docs,
        'show_upgrade_nudge': doctor_usage_pct >= 80,
    })


@login_required
@_require_clinic_admin
def manage_staff(request, role):
    """List doctors or receptionists for the clinic."""
    clinic = request.user.clinic
    staff  = clinic.staff.filter(role=role).order_by('full_name')
    return render(request, 'clinic_admin/staff.html', {
        'clinic':     clinic,
        'staff':      staff,
        'role':       role,
        'role_title': 'Doctor' if role == 'doctor' else 'Receptionist',
    })


@login_required
@_require_clinic_admin
def add_staff(request, role):
    from apps.accounts.forms import PatientRegisterForm

    clinic = request.user.clinic
    specs  = Specialization.objects.all().order_by('name') if role == 'doctor' else None

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        phone     = request.POST.get('phone', '').strip()
        password  = request.POST.get('password', '')
        sec_q     = request.POST.get('security_question', '')
        sec_a     = request.POST.get('security_answer', '').strip().lower()

        if not all([full_name, password]):
            messages.error(request, 'Full name and password are required.')
            return redirect(request.path)

        gen_email  = User.generate_staff_email(full_name, clinic.slug)
        staff_user = User.objects.create_user(
            email             = gen_email,
            full_name         = full_name,
            password          = password,
            clinic            = clinic,
            phone             = phone,
            role              = role,
            generated_email   = gen_email,
            approval_status   = 'approved' if role == 'receptionist' else 'pending',
            registration_type = 'admin_created',
            security_question = sec_q,
            security_answer   = sec_a,
        )

        if role == 'doctor':
            spec_id = request.POST.get('specialization')
            lic_no  = request.POST.get('license_number', '').strip()
            slot    = int(request.POST.get('slot_duration', 30))
            max_p   = int(request.POST.get('max_patients', 20))
            try:
                spec = Specialization.objects.get(pk=spec_id)
                Doctor.objects.create(
                    user                 = staff_user,
                    clinic               = clinic,
                    specialization       = spec,
                    license_number       = lic_no,
                    slot_duration_mins   = slot,
                    max_patients_per_day = max_p,
                    is_accepting_patients = False,  # activated on approval
                )
            except Specialization.DoesNotExist:
                messages.error(request, 'Invalid specialization.')
                staff_user.delete()
                return redirect(request.path)

        messages.success(
            request,
            f'{"Doctor" if role == "doctor" else "Receptionist"} <strong>{full_name}</strong> added. '
            f'Login email: <code>{gen_email}</code>',
        )
        return redirect('manage_staff', role=role)

    return render(request, 'clinic_admin/add_staff.html', {
        'clinic':       clinic,
        'role':         role,
        'specs':        specs,
        'sec_questions': settings.SECURITY_QUESTIONS,
        'role_title':   'Doctor' if role == 'doctor' else 'Receptionist',
    })


@login_required
@_require_clinic_admin
def toggle_staff(request, user_id):
    clinic = request.user.clinic
    user   = get_object_or_404(User, pk=user_id, clinic=clinic)
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'{user.full_name} has been {status}.')
    return redirect('manage_staff', role=user.role)


@login_required
@_require_clinic_admin
def approve_doctor(request, user_id):
    clinic = request.user.clinic
    user   = get_object_or_404(User, pk=user_id, clinic=clinic, role='doctor')
    user.approval_status = 'approved'
    user.is_active       = True
    user.save(update_fields=['approval_status', 'is_active'])
    Doctor.objects.filter(user=user).update(is_accepting_patients=True)
    messages.success(request, f'Dr. {user.full_name} approved and activated.')
    return redirect('clinic_admin_pending_doctors')


@login_required
@_require_clinic_admin
def reject_doctor_account(request, user_id):
    clinic = request.user.clinic
    user   = get_object_or_404(User, pk=user_id, clinic=clinic, role='doctor')
    user.approval_status = 'rejected'
    user.save(update_fields=['approval_status'])
    messages.warning(request, f"Dr. {user.full_name}'s account rejected.")
    return redirect('clinic_admin_pending_doctors')


@login_required
@_require_clinic_admin
def pending_doctors(request):
    clinic  = request.user.clinic
    pending = clinic.staff.filter(
        role='doctor', approval_status='pending'
    ).select_related('doctor')
    return render(request, 'clinic_admin/pending_doctors.html', {
        'clinic': clinic, 'pending': pending,
    })


@login_required
@_require_clinic_admin
def manage_services(request):
    clinic       = request.user.clinic
    current_ids  = clinic.services.filter(is_active=True).values_list('specialization_id', flat=True)
    available    = Specialization.objects.exclude(pk__in=current_ids).order_by('name')
    active_svcs  = clinic.services.filter(is_active=True).select_related('specialization')

    if request.method == 'POST':
        spec_id = request.POST.get('specialization')
        try:
            spec = Specialization.objects.get(pk=spec_id)
            svc, created = ClinicService.objects.get_or_create(
                clinic=clinic, specialization=spec,
                defaults={'is_active': True},
            )
            if not created:
                svc.is_active = True
                svc.save()
            messages.success(request, f'"{spec.name}" added to your services.')
        except Specialization.DoesNotExist:
            messages.error(request, 'Invalid specialization.')
        return redirect('manage_services')

    return render(request, 'clinic_admin/services.html', {
        'clinic': clinic, 'active_svcs': active_svcs, 'available': available,
    })


@login_required
@_require_clinic_admin
def remove_service(request, service_id):
    clinic = request.user.clinic
    svc    = get_object_or_404(ClinicService, pk=service_id, clinic=clinic)
    svc.is_active = False
    svc.save()
    messages.success(request, f'"{svc.specialization.name}" removed from services.')
    return redirect('manage_services')


@login_required
@_require_clinic_admin
def clinic_settings(request):
    clinic = request.user.clinic
    form   = ClinicUpdateForm(request.POST or None, request.FILES or None, instance=clinic)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Clinic profile updated successfully.')
        return redirect('clinic_settings')
    return render(request, 'clinic_admin/settings.html', {'clinic': clinic, 'form': form})


@login_required
@_require_clinic_admin
def subscription_page(request):
    clinic = request.user.clinic
    return render(request, 'clinic_admin/subscription.html', {
        'clinic': clinic,
        'plans':  settings.SUBSCRIPTION_PLANS,
        'plan':   settings.SUBSCRIPTION_PLANS.get(clinic.subscription_plan, {}),
    })


@login_required
@_require_clinic_admin
def upgrade_plan(request):
    if request.method != 'POST':
        return redirect('subscription_page')

    clinic    = request.user.clinic
    plan_key  = request.POST.get('plan')
    billing   = request.POST.get('billing_cycle', 'monthly')
    card_num  = request.POST.get('card_number', '').replace(' ', '')
    card_exp  = request.POST.get('card_expiry', '').strip()
    card_cvv  = request.POST.get('card_cvv', '').strip()
    card_hold = request.POST.get('card_holder', '').strip()

    if plan_key not in settings.SUBSCRIPTION_PLANS:
        messages.error(request, 'Invalid plan selected.')
        return redirect('subscription_page')
    if not card_hold:
        messages.error(request, 'Cardholder name is required.')
        return redirect('subscription_page')
    if not (card_num.isdigit() and len(card_num) >= 13):
        messages.error(request, 'Please enter a valid card number.')
        return redirect('subscription_page')
    if not card_exp or '/' not in card_exp:
        messages.error(request, 'Please enter a valid expiry date (MM/YY).')
        return redirect('subscription_page')
    if not (card_cvv.isdigit() and len(card_cvv) >= 3):
        messages.error(request, 'Please enter a valid CVV.')
        return redirect('subscription_page')

    duration = 30 if billing == 'monthly' else 365
    clinic.subscription_plan   = plan_key
    clinic.billing_cycle       = billing
    clinic.subscription_status = 'active'
    clinic.subscription_expiry = date.today() + timedelta(days=duration)
    clinic.card_last4          = card_num[-4:]
    clinic.card_brand          = _detect_card_brand(card_num)
    clinic.card_holder         = card_hold
    clinic.save()

    plan_name = settings.SUBSCRIPTION_PLANS[plan_key]['name']
    messages.success(request, f'✅ Successfully upgraded to <strong>{plan_name}</strong>!')
    return redirect('subscription_page')

def landing(request):
    hospitals = (Clinic.objects
                 .filter(approval_status='approved', is_active=True,
                         subscription_status__in=['trial','active'])
                 .prefetch_related('photos', 'services__specialization')
                 .order_by('-created_at')[:12])

    return render(request, 'landing/index.html', {
        'hospitals': hospitals,
        'plans': settings.SUBSCRIPTION_PLANS,
    })

@login_required
@_require_clinic_admin
def manage_gallery(request):
    from .models import ClinicPhoto
    clinic = request.user.clinic
    photos = clinic.photos.all().order_by('order')

    if request.method == 'POST':
        if 'upload' in request.POST:
            files = request.FILES.getlist('images')
            for i, f in enumerate(files):
                ClinicPhoto.objects.create(
                    clinic=clinic, image=f,
                    caption=request.POST.get('caption',''),
                    order=photos.count() + i,
                    is_primary=(not photos.exists() and i == 0)
                )
            messages.success(request, f'✅ {len(files)} photo(s) uploaded.')
        elif 'delete_id' in request.POST:
            ClinicPhoto.objects.filter(pk=request.POST['delete_id'], clinic=clinic).delete()
            messages.success(request, 'Photo removed.')
        elif 'set_primary' in request.POST:
            ClinicPhoto.objects.filter(clinic=clinic).update(is_primary=False)
            ClinicPhoto.objects.filter(pk=request.POST['set_primary'], clinic=clinic).update(is_primary=True)
            messages.success(request, 'Primary photo updated.')
        return redirect('manage_gallery')

    return render(request, 'clinic_admin/gallery.html', {
        'clinic': clinic, 'photos': photos,
    })