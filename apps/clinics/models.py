# apps/clinics/models.py
import re
from django.db import models
from django.utils import timezone
from django.conf import settings


def clinic_doc_path(instance, filename):
    safe = re.sub(r'[^a-zA-Z0-9]', '_', instance.clinic.name)[:30]
    return f'clinic_docs/{safe}/{filename}'


class Specialization(models.Model):
    name              = models.CharField(max_length=100, unique=True)
    description       = models.TextField(blank=True)
    icon              = models.CharField(max_length=10, default='🏥')
    common_conditions = models.TextField(blank=True)
    example_symptoms  = models.TextField(blank=True)
    when_to_visit     = models.TextField(blank=True)

    class Meta:
        db_table = 'specializations'
        ordering = ['name']

    def __str__(self):
        return self.name

    def conditions_list(self):
        return [c.strip() for c in self.common_conditions.split(',') if c.strip()]

    def symptoms_list(self):
        return [s.strip() for s in self.example_symptoms.split(',') if s.strip()]

    def image_url(self):
        """Returns a representative stock photo for this specialization."""
        topic_map = {
            'General Practice':          'doctor,clinic',
            'Cardiology':                'heart,cardiology',
            'Pediatrics':                'child,pediatrics',
            'Dermatology':               'skincare,dermatology',
            'Orthopedics':               'bones,orthopedic',
            'Neurology':                 'brain,neurology',
            'Gynecology':                'womens-health',
            'Ophthalmology':             'eye,optometry',
            'ENT (Ear, Nose & Throat)':  'ent,medical',
            'Psychiatry':                'mental-health',
            'Dentistry':                 'dental,dentist',
            'Oncology':                  'cancer-research',
            'Urology':                   'urology,medical',
            'Endocrinology':             'diabetes,medical',
            'Physiotherapy':             'physiotherapy',
            'Internal Medicine':         'hospital,medicine',
            'Gastroenterology':          'digestive,medical',
            'Rheumatology':              'joint-pain',
            'Obstetrics':                'pregnancy,maternity',
            'Emergency Medicine':        'emergency,ambulance',
        }
        topic = topic_map.get(self.name, 'hospital,medical')
        return f'https://source.unsplash.com/400x300/?{topic}&sig={self.pk}'


class Clinic(models.Model):
    APPROVAL_CHOICES = [
        ('pending',   'Pending'),
        ('approved',  'Approved'),
        ('rejected',  'Rejected'),
        ('suspended', 'Suspended'),
    ]
    PLAN_CHOICES = [
        ('trial',      'Free Trial'),
        ('starter',    'Starter'),
        ('growth',     'Growth'),
        ('enterprise', 'Enterprise'),
    ]
    SUB_STATUS_CHOICES = [
        ('pending',   'Pending'),
        ('trial',     'Trial'),
        ('active',    'Active'),
        ('expired',   'Expired'),
        ('suspended', 'Suspended'),
    ]
    BILLING_CHOICES = [('monthly', 'Monthly'), ('annual', 'Annual')]

    name    = models.CharField(max_length=150)
    address = models.TextField(blank=True)
    phone   = models.CharField(max_length=30, blank=True)
    email   = models.EmailField(blank=True)
    logo    = models.ImageField(upload_to='clinic_logos/', null=True, blank=True)
    slug    = models.SlugField(max_length=80, unique=True)

    # Approval
    approval_status  = models.CharField(max_length=20, choices=APPROVAL_CHOICES,
                                        default='pending', db_index=True)
    approval_note    = models.TextField(blank=True)
    approved_by      = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='approved_clinics'
    )
    approved_at      = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    # Subscription
    subscription_plan   = models.CharField(max_length=20, choices=PLAN_CHOICES, default='trial')
    subscription_status = models.CharField(max_length=20, choices=SUB_STATUS_CHOICES, default='pending')
    billing_cycle       = models.CharField(max_length=10, choices=BILLING_CHOICES, default='monthly')
    trial_started_at    = models.DateTimeField(null=True, blank=True)
    subscription_expiry = models.DateField(null=True, blank=True)

    # Payment
    card_last4  = models.CharField(max_length=4, blank=True)
    card_brand  = models.CharField(max_length=20, blank=True)
    card_holder = models.CharField(max_length=150, blank=True)

    # Soft delete
    is_active       = models.BooleanField(default=True)
    deleted_at      = models.DateTimeField(null=True, blank=True)
    deleted_by      = models.ForeignKey(
        'accounts.User', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='deleted_clinics'
    )
    deletion_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clinics'

    def __str__(self):
        return self.name

    @property
    def plan_info(self):
        return settings.SUBSCRIPTION_PLANS.get(self.subscription_plan, {})

    @property
    def days_remaining(self):
        if not self.subscription_expiry:
            return 0
        from datetime import date
        delta = self.subscription_expiry - date.today()
        return max(0, delta.days)

    @property
    def is_subscription_active(self):
        from datetime import date
        if self.subscription_status in ('trial', 'active'):
            if self.subscription_expiry:
                return date.today() <= self.subscription_expiry
            return True
        return False

    def activate_trial(self):
        from datetime import date, timedelta
        self.subscription_status = 'trial'
        self.trial_started_at    = timezone.now()
        self.subscription_expiry = date.today() + timedelta(days=30)
        self.save(update_fields=['subscription_status', 'trial_started_at', 'subscription_expiry'])

    def get_doctor_count(self):
        return self.doctors.filter(user__is_active=True).count()

    def get_service_names(self):
        return list(
            self.services.filter(is_active=True)
            .values_list('specialization__name', flat=True)
        )


class ClinicDocument(models.Model):
    DOC_TYPE_CHOICES = [
        ('registration_cert', 'Registration Certificate'),
        ('license',           'Medical License'),
        ('tax_cert',          'Tax Certificate'),
        ('other',             'Other'),
    ]
    clinic      = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='documents')
    doc_type    = models.CharField(max_length=30, choices=DOC_TYPE_CHOICES)
    file_name   = models.CharField(max_length=255)
    file        = models.FileField(upload_to=clinic_doc_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinic_documents'

    def __str__(self):
        return f'{self.clinic.name} — {self.doc_type}'


class ClinicService(models.Model):
    clinic         = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='services')
    specialization = models.ForeignKey(Specialization, on_delete=models.CASCADE)
    description    = models.TextField(blank=True)
    is_active      = models.BooleanField(default=True)

    class Meta:
        db_table = 'clinic_services'
        unique_together = ('clinic', 'specialization')

    def __str__(self):
        return f'{self.clinic.name} — {self.specialization.name}'