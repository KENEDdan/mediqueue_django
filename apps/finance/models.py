from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


class PlatformSubscriptionPayment(models.Model):
    """
    Every subscription payment made by a clinic to the platform (KENEDY).
    This is what appears in the superadmin revenue dashboard.
    """
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('paid',     'Paid'),
        ('failed',   'Failed'),
        ('refunded', 'Refunded'),
        ('disputed', 'Disputed'),
    ]
    METHOD_CHOICES = [
        ('stripe',        'Stripe (Card)'),
        ('manual_card',   'Manual Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('other',         'Other'),
    ]

    reference       = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    clinic          = models.ForeignKey(
        'clinics.Clinic', on_delete=models.PROTECT,
        related_name='subscription_payments'
    )
    plan            = models.CharField(max_length=20)
    billing_cycle   = models.CharField(max_length=10)
    amount          = models.DecimalField(max_digits=10, decimal_places=2)
    currency        = models.CharField(max_length=10, default='USD')
    method          = models.CharField(max_length=30, choices=METHOD_CHOICES, default='stripe')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Stripe specifics
    stripe_payment_intent_id = models.CharField(max_length=200, blank=True)
    stripe_charge_id         = models.CharField(max_length=200, blank=True)
    card_last4               = models.CharField(max_length=4, blank=True)
    card_brand               = models.CharField(max_length=20, blank=True)

    # Period this payment covers
    period_start = models.DateField(null=True, blank=True)
    period_end   = models.DateField(null=True, blank=True)

    failure_reason = models.TextField(blank=True)
    notes          = models.TextField(blank=True)

    paid_at    = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'platform_subscription_payments'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.clinic.name} — {self.plan} — {self.amount} {self.currency}'


class ClinicPayoutAccount(models.Model):
    """
    The bank/mobile money account a clinic uses to RECEIVE patient booking fees.
    Receptionist uses this info to tell patients where to pay.
    """
    METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('mtn_momo',      'MTN Mobile Money'),
        ('mpesa',         'M-Pesa'),
        ('airtel_money',  'Airtel Money'),
        ('orange_money',  'Orange Money'),
        ('stripe',        'Stripe'),
        ('paypal',        'PayPal'),
        ('cash',          'Cash Only'),
        ('multiple',      'Multiple Methods'),
    ]

    clinic         = models.OneToOneField(
        'clinics.Clinic', on_delete=models.CASCADE,
        related_name='payout_account'
    )
    method         = models.CharField(max_length=30, choices=METHOD_CHOICES)
    account_name   = models.CharField(max_length=150, blank=True)
    account_number = models.CharField(max_length=100, blank=True,
                                      help_text='Bank account or mobile number')
    bank_name      = models.CharField(max_length=100, blank=True)
    bank_branch    = models.CharField(max_length=100, blank=True)
    swift_code     = models.CharField(max_length=20, blank=True)
    paypal_email   = models.EmailField(blank=True)
    stripe_account_id = models.CharField(max_length=100, blank=True)
    instructions   = models.TextField(
        blank=True,
        help_text='Payment instructions shown to patients'
    )
    booking_fee_default = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Default booking fee for this clinic'
    )
    currency       = models.CharField(max_length=10, default='USD')
    is_active      = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clinic_payout_accounts'

    def __str__(self):
        return f'{self.clinic.name} — {self.method}'


class ClinicTransaction(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('refunded', 'Refunded'),
    ]

    reference    = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    clinic       = models.ForeignKey(
        'clinics.Clinic', on_delete=models.PROTECT,
        related_name='transactions'
    )
    # Changed from OneToOneField to AppointmentPayment → now FK to Appointment
    appointment  = models.ForeignKey(
        'appointments.Appointment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='clinic_transactions'
    )
    patient      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='payment_transactions', null=True, blank=True
    )
    walkin_patient_name = models.CharField(max_length=150, blank=True)
    amount       = models.DecimalField(max_digits=10, decimal_places=2)
    currency     = models.CharField(max_length=10, default='USD')
    method       = models.CharField(max_length=30)
    reference_no = models.CharField(max_length=200, blank=True)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                     default='pending')
    verified_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_transactions'
    )
    notes        = models.TextField(blank=True)
    paid_at      = models.DateTimeField(default=timezone.now)
    verified_at  = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'clinic_transactions'
        ordering = ['-paid_at']

    def __str__(self):
        return f'{self.clinic.name} — {self.amount} {self.currency} ({self.status})'

    @property
    def patient_display(self):
        if self.patient:
            return self.patient.full_name
        return self.walkin_patient_name or 'Unknown'


class PlatformFinanceSummary(models.Model):
    """
    Monthly snapshot of platform revenue — auto-generated by Celery task.
    Used for the superadmin revenue chart.
    """
    month                = models.DateField(unique=True)
    total_revenue        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_subscriptions  = models.IntegerField(default=0)
    starter_revenue      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    growth_revenue       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    enterprise_revenue   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    new_clinics          = models.IntegerField(default=0)
    churned_clinics      = models.IntegerField(default=0)
    generated_at         = models.DateTimeField(auto_now=True)

class Meta:
        db_table = 'platform_finance_summary'
        ordering = ['-month']

def __str__(self):
        return f'{self.month.strftime("%B %Y")} — ${self.total_revenue}'
    
class PlatformCommission(models.Model):
    """
    Platform takes a % of every patient booking fee.
    Default: 5% of booking fee goes to MediQueue.
    """
    clinic       = models.ForeignKey('clinics.Clinic', on_delete=models.PROTECT)
    transaction  = models.OneToOneField(
        ClinicTransaction, on_delete=models.PROTECT,
        related_name='commission'
    )
    gross_amount    = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
    net_to_clinic   = models.DecimalField(max_digits=10, decimal_places=2)
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'platform_commissions'