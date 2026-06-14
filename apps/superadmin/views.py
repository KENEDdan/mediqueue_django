from datetime import date, timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.utils import timezone

from apps.clinics.models import Clinic, ClinicDocument
from apps.accounts.models import User
from apps.appointments.models import Appointment
from apps.notifications.utils import notify_user



def _require_super_admin(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.role != 'super_admin':
            messages.error(request, 'Access denied — Super Admin only.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@_require_super_admin
def dashboard(request):
    stats = {
        'total_clinics':   Clinic.objects.filter(is_active=True, deleted_at__isnull=True).count(),
        'pending_clinics': Clinic.objects.filter(approval_status='pending').count(),
        'approved_clinics':Clinic.objects.filter(approval_status='approved', is_active=True).count(),
        'total_patients':  User.objects.filter(role='patient').count(),
        'total_doctors':   User.objects.filter(role='doctor', is_active=True).count(),
        'total_appts':     Appointment.objects.count(),
    }
    pending = (Clinic.objects
               .filter(approval_status='pending')
               .prefetch_related('documents', 'staff')
               .order_by('created_at')[:5])
    return render(request, 'superadmin/dashboard.html', {'stats': stats, 'pending': pending})


@login_required
@_require_super_admin
def pending_clinics(request):
    clinics = (Clinic.objects
               .filter(approval_status='pending')
               .prefetch_related('documents', 'staff')
               .order_by('created_at'))
    return render(request, 'superadmin/pending_clinics.html', {'clinics': clinics})


@login_required
@_require_super_admin
def approve_clinic(request, clinic_id):
    clinic = get_object_or_404(Clinic, pk=clinic_id, approval_status='pending')
    if request.method == 'POST':
        clinic.approval_status = 'approved'
        clinic.approved_by     = request.user
        clinic.approved_at     = timezone.now()
        clinic.save()
        clinic.activate_trial()

        admin_user = clinic.staff.filter(role='clinic_admin').first()
        if admin_user:
            notify_user(
                user=admin_user, type='approval',
                title='🎉 Your hospital has been approved!',
                message=(
                    f'Great news! "{clinic.name}" has been approved and is now live on MediQueue.\n\n'
                    f'Stage: APPROVED — Active on a 30-day free trial.\n'
                    f'Trial expires: {clinic.subscription_expiry}\n\n'
                    f'You can now log in, add doctors and receptionists, set up your services, '
                    f'and start receiving appointment requests from patients.'
                ),
                link='/staff-login/',
                email_subject=f'🎉 Your hospital "{clinic.name}" is approved on MediQueue!',
                email_template='emails/generic_notification.html',
                email_context={'link_url': 'https://mediqueue.health/staff-login/'}
            )
        messages.success(request, f'✅ {clinic.name} approved and activated.')
        return redirect('superadmin:pending_clinics')
    return render(request, 'superadmin/approve_clinic.html', {'clinic': clinic})


@login_required
@_require_super_admin
def reject_clinic(request, clinic_id):
    clinic = get_object_or_404(Clinic, pk=clinic_id, approval_status='pending')
    if request.method == 'POST':
        reason = request.POST.get('reason','').strip()
        clinic.approval_status  = 'rejected'
        clinic.rejection_reason = reason
        clinic.save()

        admin_user = clinic.staff.filter(role='clinic_admin').first()
        if admin_user:
            notify_user(
                user=admin_user, type='approval',
                title='Update on your hospital application',
                message=(
                    f'Your application for "{clinic.name}" was not approved at this time.\n\n'
                    f'Stage: NOT APPROVED\n'
                    f'Reason: {reason}\n\n'
                    f'You can correct the issue and submit a new application, '
                    f'or contact our support team for clarification.'
                ),
                link='/clinics/register/',
                email_subject=f'[MediQueue] Update on your application for "{clinic.name}"',
                email_template='emails/generic_notification.html',
            )
        messages.success(request, f'{clinic.name} rejected.')
        return redirect('superadmin:pending_clinics')
    return render(request, 'superadmin/reject_clinic.html', {'clinic': clinic})

@login_required
@_require_super_admin
def all_clinics(request):
    show_deleted = request.GET.get('deleted') == '1'
    qs = Clinic.objects.all() if show_deleted else Clinic.objects.filter(deleted_at__isnull=True)
    return render(request, 'superadmin/all_clinics.html', {
        'clinics': qs.order_by('-created_at'), 'show_deleted': show_deleted,
    })


@login_required
@_require_super_admin
def delete_clinic(request, clinic_id):
    clinic = get_object_or_404(Clinic, pk=clinic_id, deleted_at__isnull=True)
    if request.method == 'POST':
        reason = request.POST.get('reason', '').strip()
        if not reason:
            messages.error(request, 'Please provide a deletion reason.')
            return redirect(request.path)
        clinic.deleted_at      = timezone.now()
        clinic.deleted_by      = request.user
        clinic.deletion_reason = reason
        clinic.is_active       = False
        clinic.save()
        clinic.staff.update(is_active=False)
        messages.success(request, f'{clinic.name} soft-deleted. All data preserved.')
        return redirect('superadmin:all_clinics')
    return render(request, 'superadmin/delete_clinic.html', {'clinic': clinic})


@login_required
@_require_super_admin
def restore_clinic(request, clinic_id):
    clinic = get_object_or_404(Clinic, pk=clinic_id)
    clinic.deleted_at = None; clinic.deleted_by = None
    clinic.deletion_reason = ''; clinic.is_active = True
    clinic.save()
    clinic.staff.update(is_active=True)
    messages.success(request, f'{clinic.name} restored successfully.')
    return redirect('superadmin:all_clinics')


@login_required
@_require_super_admin
def all_users(request):
    role = request.GET.get('role', '')
    qs   = User.objects.select_related('clinic').order_by('-created_at')
    if role:
        qs = qs.filter(role=role)
    return render(request, 'superadmin/all_users.html', {
        'users': qs[:500], 'role_filter': role,
        'roles': User.ROLE_CHOICES,
    })


@login_required
@_require_super_admin
def platform_stats(request):
    from django.db.models import Count
    appts_by_status = dict(
        Appointment.objects.values('status').annotate(c=Count('id')).values_list('status', 'c')
    )
    clinics_by_plan = dict(
        Clinic.objects.filter(is_active=True).values('subscription_plan').annotate(c=Count('id')).values_list('subscription_plan', 'c')
    )
    return render(request, 'superadmin/stats.html', {
        'appts_by_status': appts_by_status,
        'clinics_by_plan': clinics_by_plan,
        'total_revenue_estimate': sum(
            settings.SUBSCRIPTION_PLANS.get(plan, {}).get('price_monthly', 0) * count
            for plan, count in clinics_by_plan.items()
        ),
    })