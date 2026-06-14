from django.db import models
from django.conf import settings
from django.utils import timezone


class MedicalReport(models.Model):
    """Doctor's formal report for a completed appointment."""
    appointment  = models.OneToOneField(
        'appointments.Appointment', on_delete=models.CASCADE,
        related_name='medical_report'
    )
    clinic       = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE,
                                     related_name='medical_reports')
    patient      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='medical_reports'
    )
    doctor       = models.ForeignKey(
        'doctors.Doctor', on_delete=models.CASCADE,
        related_name='medical_reports'
    )

    # Report content
    chief_complaint    = models.TextField(help_text="Patient's main complaint")
    history            = models.TextField(blank=True, help_text="History of present illness")
    examination_notes  = models.TextField(blank=True, help_text="Physical examination findings")
    diagnosis          = models.TextField(help_text="Diagnosis / Impression")
    treatment_plan     = models.TextField(blank=True, help_text="Treatment / management plan")
    prescriptions      = models.TextField(blank=True, help_text="Medications prescribed")
    follow_up_date     = models.DateField(null=True, blank=True)
    follow_up_notes    = models.TextField(blank=True)
    additional_notes   = models.TextField(blank=True)

    # Vitals (optional)
    blood_pressure     = models.CharField(max_length=20, blank=True)
    pulse_rate         = models.CharField(max_length=20, blank=True)
    temperature        = models.CharField(max_length=20, blank=True)
    weight             = models.CharField(max_length=20, blank=True)
    height             = models.CharField(max_length=20, blank=True)
    blood_oxygen       = models.CharField(max_length=20, blank=True)

    is_shared_with_patient = models.BooleanField(default=True)
    created_at  = models.DateTimeField(default=timezone.now)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'medical_reports'

    def __str__(self):
        return f'Report for {self.patient.full_name} — {self.created_at.date()}'


class WalkInPatient(models.Model):
    """Clinic-registered patient without a MediQueue account."""
    GENDER_CHOICES = [('Male','Male'),('Female','Female'),('Other','Other')]
    BLOOD_CHOICES  = [
        ('A+','A+'),('A-','A-'),('B+','B+'),('B-','B-'),
        ('AB+','AB+'),('AB-','AB-'),('O+','O+'),('O-','O-'),('Unknown','Unknown'),
    ]

    clinic        = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE,
                                      related_name='walkin_patients')
    full_name     = models.CharField(max_length=150)
    phone         = models.CharField(max_length=30, blank=True)
    email         = models.EmailField(blank=True)
    gender        = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address       = models.TextField(blank=True)
    blood_group   = models.CharField(max_length=10, choices=BLOOD_CHOICES, default='Unknown')
    allergies     = models.TextField(blank=True)
    chronic_conditions = models.TextField(blank=True)
    emergency_contact  = models.CharField(max_length=150, blank=True)
    emergency_phone    = models.CharField(max_length=30, blank=True)
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='registered_walkin_patients'
    )
    created_at    = models.DateTimeField(default=timezone.now)
    updated_at    = models.DateTimeField(auto_now=True)
    notes         = models.TextField(blank=True)

    class Meta:
        db_table = 'walkin_patients'

    def __str__(self):
        return f'{self.full_name} @ {self.clinic.name}'

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        return (date.today() - self.date_of_birth).days // 365


class WalkInVisit(models.Model):
    """A single clinic visit / consultation record for a walk-in patient."""
    patient     = models.ForeignKey(WalkInPatient, on_delete=models.CASCADE,
                                    related_name='visits')
    clinic      = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE,
                                    related_name='walkin_visits')
    doctor      = models.ForeignKey(
        'doctors.Doctor', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='walkin_visits'
    )
    attended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='attended_walkin_visits'
    )

    visit_date         = models.DateField(default=timezone.now)
    chief_complaint    = models.TextField()
    examination_notes  = models.TextField(blank=True)
    diagnosis          = models.TextField(blank=True)
    treatment_plan     = models.TextField(blank=True)
    prescriptions      = models.TextField(blank=True)
    follow_up_date     = models.DateField(null=True, blank=True)

    # Vitals
    blood_pressure = models.CharField(max_length=20, blank=True)
    pulse_rate     = models.CharField(max_length=20, blank=True)
    temperature    = models.CharField(max_length=20, blank=True)
    weight         = models.CharField(max_length=20, blank=True)
    blood_oxygen   = models.CharField(max_length=20, blank=True)

    amount_charged = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_notes  = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'walkin_visits'
        ordering = ['-visit_date']

    def __str__(self):
        return f'{self.patient.full_name} — {self.visit_date}'