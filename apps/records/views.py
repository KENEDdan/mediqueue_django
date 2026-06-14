from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import MedicalReport, WalkInPatient, WalkInVisit
from apps.appointments.models import Appointment
from apps.doctors.models import Doctor


def _require_clinic_staff(view_func):
    from functools import wraps
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or \
                request.user.role not in ('clinic_admin', 'receptionist', 'doctor'):
            messages.error(request, 'Access denied.')
            return redirect('staff_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ── Medical Reports ────────────────────────────────────────────

@login_required
def write_medical_report(request, appt_id):
    """Doctor writes/updates a medical report for a completed appointment."""
    if request.user.role != 'doctor':
        messages.error(request, 'Only doctors can write medical reports.')
        return redirect('dashboard')

    doctor = get_object_or_404(Doctor, user=request.user)
    appt   = get_object_or_404(
        Appointment, pk=appt_id, doctor=doctor,
        status__in=['confirmed', 'completed']
    )
    existing = getattr(appt, 'medical_report', None)

    if request.method == 'POST':
        data = {
            'appointment':        appt,
            'clinic':             appt.clinic,
            'patient':            appt.patient,
            'doctor':             doctor,
            'chief_complaint':    request.POST.get('chief_complaint', ''),
            'history':            request.POST.get('history', ''),
            'examination_notes':  request.POST.get('examination_notes', ''),
            'diagnosis':          request.POST.get('diagnosis', ''),
            'treatment_plan':     request.POST.get('treatment_plan', ''),
            'prescriptions':      request.POST.get('prescriptions', ''),
            'follow_up_date':     request.POST.get('follow_up_date') or None,
            'follow_up_notes':    request.POST.get('follow_up_notes', ''),
            'additional_notes':   request.POST.get('additional_notes', ''),
            'blood_pressure':     request.POST.get('blood_pressure', ''),
            'pulse_rate':         request.POST.get('pulse_rate', ''),
            'temperature':        request.POST.get('temperature', ''),
            'weight':             request.POST.get('weight', ''),
            'height':             request.POST.get('height', ''),
            'blood_oxygen':       request.POST.get('blood_oxygen', ''),
            'is_shared_with_patient': request.POST.get('share', 'on') == 'on',
        }

        if not data['chief_complaint'] or not data['diagnosis']:
            messages.error(request, 'Chief complaint and diagnosis are required.')
            return redirect(request.path)

        if existing:
            for key, val in data.items():
                if key not in ('appointment', 'clinic', 'patient', 'doctor'):
                    setattr(existing, key, val)
            existing.save()
            report = existing
        else:
            report = MedicalReport.objects.create(**data)

        # Generate QR code for prescriptions
        if report.prescriptions:
            try:
                report.generate_qr_code()
            except Exception as e:
                print(f'[QR] Failed: {e}')

        # Mark appointment completed
        if appt.status != 'completed':
            from django.utils import timezone
            appt.status       = 'completed'
            appt.completed_at = timezone.now()
            appt.save()

        # Notify patient
        if report.is_shared_with_patient:
            try:
                from apps.notifications.utils import notify_medical_report_ready
                notify_medical_report_ready(report)
            except Exception as e:
                print(f'[Email] {e}')

        messages.success(
            request,
            '✅ Medical report saved and shared with patient.'
            if report.is_shared_with_patient
            else '✅ Medical report saved (not shared with patient).'
        )
        return redirect('doctor_appointments')

    vitals = [
        ('blood_pressure', 'Blood Pressure', 'e.g. 120/80 mmHg'),
        ('pulse_rate',     'Pulse Rate',     'e.g. 72 bpm'),
        ('temperature',    'Temperature',    'e.g. 37.2°C'),
        ('weight',         'Weight',         'e.g. 70 kg'),
        ('height',         'Height',         'e.g. 175 cm'),
        ('blood_oxygen',   'Blood Oxygen',   'e.g. 98%'),
    ]
    return render(request, 'records/medical_report.html', {
        'appt':   appt,
        'doctor': doctor,
        'report': existing,
        'vitals': vitals,
    })


@login_required
@_require_clinic_staff
def clinic_patient_records(request):
    """All medical reports for this clinic."""
    clinic  = request.user.clinic
    search  = request.GET.get('q', '').strip()
    reports = (MedicalReport.objects
               .filter(clinic=clinic)
               .select_related('patient', 'doctor__user', 'appointment')
               .order_by('-created_at'))
    if search:
        reports = reports.filter(patient__full_name__icontains=search)
    return render(request, 'records/patient_records.html', {
        'clinic': clinic, 'reports': reports, 'search': search,
    })


# ── Walk-in Patients ───────────────────────────────────────────

@login_required
@_require_clinic_staff
def walkin_patient_list(request):
    clinic   = request.user.clinic
    search   = request.GET.get('q', '').strip()
    patients = WalkInPatient.objects.filter(clinic=clinic).order_by('full_name')
    if search:
        patients = patients.filter(full_name__icontains=search)
    return render(request, 'records/walkin_list.html', {
        'clinic': clinic, 'patients': patients, 'search': search,
    })


@login_required
@_require_clinic_staff
def walkin_patient_create(request):
    clinic  = request.user.clinic
    doctors = Doctor.objects.filter(
        clinic=clinic, user__is_active=True
    ).select_related('user', 'specialization')

    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        if not full_name:
            messages.error(request, 'Full name is required.')
            return redirect(request.path)

        dob     = request.POST.get('date_of_birth') or None
        patient = WalkInPatient.objects.create(
            clinic             = clinic,
            full_name          = full_name,
            phone              = request.POST.get('phone', ''),
            email              = request.POST.get('email', ''),
            gender             = request.POST.get('gender', ''),
            date_of_birth      = dob,
            address            = request.POST.get('address', ''),
            blood_group        = request.POST.get('blood_group', 'Unknown'),
            allergies          = request.POST.get('allergies', ''),
            chronic_conditions = request.POST.get('chronic_conditions', ''),
            emergency_contact  = request.POST.get('emergency_contact', ''),
            emergency_phone    = request.POST.get('emergency_phone', ''),
            notes              = request.POST.get('notes', ''),
            registered_by      = request.user,
        )

        # Create initial visit if complaint provided
        complaint = request.POST.get('chief_complaint', '').strip()
        if complaint:
            doctor_id = request.POST.get('doctor_id')
            doctor    = (Doctor.objects
                         .filter(pk=doctor_id, clinic=clinic).first()
                         if doctor_id else None)
            WalkInVisit.objects.create(
                patient           = patient,
                clinic            = clinic,
                doctor            = doctor,
                attended_by       = request.user,
                visit_date        = request.POST.get('visit_date') or date.today(),
                chief_complaint   = complaint,
                examination_notes = request.POST.get('examination_notes', ''),
                diagnosis         = request.POST.get('diagnosis', ''),
                treatment_plan    = request.POST.get('treatment_plan', ''),
                prescriptions     = request.POST.get('prescriptions', ''),
                blood_pressure    = request.POST.get('blood_pressure', ''),
                pulse_rate        = request.POST.get('pulse_rate', ''),
                temperature       = request.POST.get('temperature', ''),
                weight            = request.POST.get('weight', ''),
                blood_oxygen      = request.POST.get('blood_oxygen', ''),
                amount_charged    = request.POST.get('amount_charged') or 0,
                amount_paid       = request.POST.get('amount_paid') or 0,
                payment_notes     = request.POST.get('payment_notes', ''),
            )

        messages.success(request, f'✅ Walk-in patient {full_name} registered.')
        return redirect('walkin_patient_detail', pk=patient.pk)

    return render(request, 'records/walkin_form.html', {
        'clinic':       clinic,
        'doctors':      doctors,
        'blood_groups': WalkInPatient.BLOOD_CHOICES,
        'today':        date.today().isoformat(),
    })


@login_required
@_require_clinic_staff
def walkin_patient_detail(request, pk):
    clinic  = request.user.clinic
    patient = get_object_or_404(WalkInPatient, pk=pk, clinic=clinic)
    visits  = patient.visits.select_related(
        'doctor__user', 'attended_by'
    ).order_by('-visit_date')
    doctors = Doctor.objects.filter(
        clinic=clinic, user__is_active=True
    ).select_related('user', 'specialization')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_visit':
            complaint = request.POST.get('chief_complaint', '').strip()
            if not complaint:
                messages.error(request, 'Chief complaint is required.')
                return redirect(request.path)
            doctor_id = request.POST.get('doctor_id')
            doctor    = (Doctor.objects
                         .filter(pk=doctor_id, clinic=clinic).first()
                         if doctor_id else None)
            WalkInVisit.objects.create(
                patient           = patient,
                clinic            = clinic,
                doctor            = doctor,
                attended_by       = request.user,
                visit_date        = request.POST.get('visit_date') or date.today(),
                chief_complaint   = complaint,
                examination_notes = request.POST.get('examination_notes', ''),
                diagnosis         = request.POST.get('diagnosis', ''),
                treatment_plan    = request.POST.get('treatment_plan', ''),
                prescriptions     = request.POST.get('prescriptions', ''),
                blood_pressure    = request.POST.get('blood_pressure', ''),
                pulse_rate        = request.POST.get('pulse_rate', ''),
                temperature       = request.POST.get('temperature', ''),
                weight            = request.POST.get('weight', ''),
                blood_oxygen      = request.POST.get('blood_oxygen', ''),
                amount_charged    = request.POST.get('amount_charged') or 0,
                amount_paid       = request.POST.get('amount_paid') or 0,
                payment_notes     = request.POST.get('payment_notes', ''),
            )
            messages.success(request, '✅ Visit record added.')
            return redirect('walkin_patient_detail', pk=pk)

    vital_fields = [
        ('blood_pressure', 'BP',     '120/80'),
        ('pulse_rate',     'Pulse',  '72 bpm'),
        ('temperature',    'Temp',   '37°C'),
        ('weight',         'Weight', 'kg'),
        ('blood_oxygen',   'O₂',     '98%'),
    ]
    return render(request, 'records/walkin_detail.html', {
        'clinic':       clinic,
        'patient':      patient,
        'visits':       visits,
        'doctors':      doctors,
        'today':        date.today().isoformat(),
        'vital_fields': vital_fields,
    })


# ── Lab Tests ──────────────────────────────────────────────────

@login_required
def request_lab_test(request, appt_id):
    """Doctor requests a lab test for a patient."""
    if request.user.role != 'doctor':
        messages.error(request, 'Only doctors can request lab tests.')
        return redirect('dashboard')

    from .models import LabTestRequest
    doctor = get_object_or_404(Doctor, user=request.user)
    appt   = get_object_or_404(Appointment, pk=appt_id, doctor=doctor)

    if request.method == 'POST':
        test_name = request.POST.get('test_name', '').strip()
        if not test_name:
            messages.error(request, 'Test name is required.')
            return redirect(request.path)

        lab = LabTestRequest.objects.create(
            appointment  = appt,
            clinic       = appt.clinic,
            patient      = appt.patient,
            doctor       = doctor,
            test_name    = test_name,
            description  = request.POST.get('description', '').strip(),
            urgency      = request.POST.get('urgency', 'routine'),
            instructions = request.POST.get('instructions', '').strip(),
            lab_name     = request.POST.get('lab_name', '').strip(),
        )
        try:
            lab.generate_qr()
        except Exception as e:
            print(f'[QR] Lab QR failed: {e}')

        messages.success(request, f'✅ Lab test "{test_name}" requested.')
        return redirect('doctor_appointments')

    from .models import LabTestRequest
    existing_labs = LabTestRequest.objects.filter(appointment=appt)
    common_tests  = [
        'Full Blood Count (FBC)',
        'Comprehensive Metabolic Panel',
        'Lipid Panel',
        'Thyroid Function Tests (TFT)',
        'Liver Function Tests (LFT)',
        'Kidney Function Tests (KFT/RFT)',
        'Random Blood Sugar (RBS)',
        'Fasting Blood Sugar (FBS)',
        'HbA1c (Diabetes monitoring)',
        'Urinalysis',
        'Malaria Rapid Test',
        'HIV Test',
        'Pregnancy Test (urine hCG)',
        'Chest X-Ray',
        'Abdominal Ultrasound',
        'ECG / EKG',
        'Sputum Culture (TB)',
        'Blood Culture',
        'Stool Analysis',
        'CD4 Count',
    ]
    return render(request, 'records/lab_test_form.html', {
        'appt':          appt,
        'existing_labs': existing_labs,
        'common_tests':  common_tests,
    })


@login_required
def patient_lab_tests(request):
    """Patient views their lab test requests."""
    if request.user.role != 'patient':
        return redirect('dashboard')
    from .models import LabTestRequest
    labs = LabTestRequest.objects.filter(
        patient=request.user
    ).select_related('doctor__user', 'clinic').order_by('-requested_at')
    return render(request, 'records/patient_lab_tests.html', {'labs': labs})


# ── PDF Download ───────────────────────────────────────────────

@login_required
def download_medical_report_pdf(request, report_id):
    """Generate and download a PDF of a medical report."""
    report = get_object_or_404(MedicalReport, pk=report_id)

    is_patient      = (request.user == report.patient)
    is_clinic_staff = (request.user.clinic and
                       request.user.clinic == report.clinic and
                       request.user.role in ('clinic_admin', 'doctor', 'receptionist'))
    is_own_report   = (hasattr(request.user, 'doctor') and
                       request.user.doctor == report.doctor)

    if not (is_patient or is_clinic_staff or is_own_report):
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.units import cm
        from django.http import HttpResponse
        import io

        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                    leftMargin=2*cm, rightMargin=2*cm,
                                    topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        primary = rl_colors.HexColor('#0B4F6C')
        success = rl_colors.HexColor('#2D9E6B')
        muted   = rl_colors.HexColor('#5A6A7A')

        h1 = ParagraphStyle('H1', parent=styles['Heading1'],
                              textColor=primary, fontSize=20, spaceAfter=4)
        h2 = ParagraphStyle('H2', parent=styles['Heading2'],
                              textColor=primary, fontSize=13, spaceAfter=4)
        normal = ParagraphStyle('N', parent=styles['Normal'],
                                  fontSize=10, spaceAfter=6, leading=14)

        story.append(Paragraph('MediQueue', h1))
        story.append(Paragraph('CONFIDENTIAL MEDICAL REPORT',
                                ParagraphStyle('sub', parent=styles['Normal'],
                                               fontSize=11, textColor=muted, spaceAfter=2)))
        story.append(HRFlowable(width='100%', color=primary, thickness=2, spaceAfter=12))

        info_data = [
            ['Patient', report.patient.full_name,
             'Date', report.created_at.strftime('%d %B %Y')],
            ['Clinic', report.clinic.name,
             'Doctor', f'Dr. {report.doctor.user.full_name}'],
            ['Report #', f'MQ-{report.pk:06d}',
             'Specialization',
             report.doctor.specialization.name if report.doctor.specialization else '—'],
        ]
        info_table = Table(info_data, colWidths=[3*cm, 7*cm, 3*cm, 5*cm])
        info_table.setStyle(TableStyle([
            ('FONTNAME',      (0,0),(-1,-1),'Helvetica'),
            ('FONTNAME',      (0,0),(0,-1),'Helvetica-Bold'),
            ('FONTNAME',      (2,0),(2,-1),'Helvetica-Bold'),
            ('FONTSIZE',      (0,0),(-1,-1), 9),
            ('TOPPADDING',    (0,0),(-1,-1), 5),
            ('BOTTOMPADDING', (0,0),(-1,-1), 5),
            ('GRID',          (0,0),(-1,-1), 0.3, rl_colors.HexColor('#CED6DE')),
            ('BACKGROUND',    (0,0),(0,-1),  rl_colors.HexColor('#F0F4F8')),
            ('BACKGROUND',    (2,0),(2,-1),  rl_colors.HexColor('#F0F4F8')),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.4*cm))

        # Vitals
        vitals = []
        for attr, label in [('blood_pressure','Blood Pressure'),
                              ('pulse_rate','Pulse Rate'),
                              ('temperature','Temperature'),
                              ('weight','Weight'),
                              ('height','Height'),
                              ('blood_oxygen','Blood Oxygen')]:
            val = getattr(report, attr, '')
            if val:
                vitals.append((label, val))

        if vitals:
            story.append(Paragraph('VITAL SIGNS', h2))
            rows = [vitals[i:i+3] for i in range(0, len(vitals), 3)]
            for row in rows:
                while len(row) < 3:
                    row.append(('', ''))
                flat = []
                for label, val in row:
                    flat.extend([label, val])
                t = Table([flat], colWidths=[3.5*cm]*6)
                t.setStyle(TableStyle([
                    ('FONTNAME',      (0,0),(-1,-1),'Helvetica'),
                    ('FONTNAME',      (0,0),(0,0),'Helvetica-Bold'),
                    ('FONTNAME',      (2,0),(2,0),'Helvetica-Bold'),
                    ('FONTNAME',      (4,0),(4,0),'Helvetica-Bold'),
                    ('FONTSIZE',      (0,0),(-1,-1), 9),
                    ('BACKGROUND',    (0,0),(0,0), rl_colors.HexColor('#F0F4F8')),
                    ('BACKGROUND',    (2,0),(2,0), rl_colors.HexColor('#F0F4F8')),
                    ('BACKGROUND',    (4,0),(4,0), rl_colors.HexColor('#F0F4F8')),
                    ('GRID',          (0,0),(-1,-1), 0.3, rl_colors.HexColor('#CED6DE')),
                    ('TOPPADDING',    (0,0),(-1,-1), 5),
                    ('BOTTOMPADDING', (0,0),(-1,-1), 5),
                ]))
                story.append(t)
            story.append(Spacer(1, 0.3*cm))

        def add_section(title, content):
            if not content:
                return
            story.append(Paragraph(title, h2))
            story.append(Paragraph(content.replace('\n', '<br/>'), normal))
            story.append(Spacer(1, 0.2*cm))

        add_section('CHIEF COMPLAINT', report.chief_complaint)
        add_section('HISTORY', report.history)
        add_section('EXAMINATION FINDINGS', report.examination_notes)

        if report.diagnosis:
            story.append(Paragraph('DIAGNOSIS', h2))
            diag_table = Table(
                [[Paragraph(report.diagnosis, normal)]],
                colWidths=[17*cm]
            )
            diag_table.setStyle(TableStyle([
                ('BACKGROUND',    (0,0),(-1,-1), rl_colors.HexColor('#F0FFF8')),
                ('LEFTPADDING',   (0,0),(-1,-1), 12),
                ('TOPPADDING',    (0,0),(-1,-1), 8),
                ('BOTTOMPADDING', (0,0),(-1,-1), 8),
                ('BOX',           (0,0),(-1,-1), 1, success),
            ]))
            story.append(diag_table)
            story.append(Spacer(1, 0.3*cm))

        add_section('TREATMENT PLAN', report.treatment_plan)
        add_section('PRESCRIPTIONS', report.prescriptions)
        add_section('ADDITIONAL NOTES', report.additional_notes)

        if report.follow_up_date:
            story.append(Paragraph('FOLLOW-UP', h2))
            story.append(Paragraph(
                f'<b>Date:</b> {report.follow_up_date}<br/>'
                f'{report.follow_up_notes or ""}', normal
            ))

        story.append(Spacer(1, 0.5*cm))
        story.append(HRFlowable(width='100%', color=muted, thickness=0.5))
        story.append(Paragraph(
            f'<font size=8 color="#5A6A7A">Generated by MediQueue — '
            f'{report.created_at.strftime("%d %B %Y")} — '
            f'This document is confidential.</font>',
            styles['Normal']
        ))

        if report.qr_code:
            from reportlab.platypus import Image as RLImage
            story.append(Spacer(1, 0.3*cm))
            story.append(Paragraph(
                '<font size=8 color="#5A6A7A">Prescription QR Code:</font>',
                styles['Normal']
            ))
            try:
                story.append(RLImage(report.qr_code.path, width=3*cm, height=3*cm))
            except Exception:
                pass

        doc.build(story)
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'attachment; filename="MediQueue-Report-{report.pk:06d}.pdf"'
        )
        return response

    except ImportError:
        messages.error(request, 'PDF generation requires reportlab. Run: pip install reportlab')
        return redirect('patient_reports')