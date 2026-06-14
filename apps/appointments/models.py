from django.db import models
from django.conf import settings
from django.utils import timezone


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('pending',           'Pending Review'),
        ('proposed',          'Slot Proposed'),
        ('accepted',          'Patient Accepted'),
        ('awaiting_payment',  'Awaiting Payment'),
        ('payment_submitted', 'Payment Submitted'),
        ('confirmed',         'Confirmed'),
        ('completed',         'Completed'),
        ('cancelled',         'Cancelled'),
        ('no_show',           'No Show'),
    ]
    TIME_OF_DAY = [
        ('Morning',   'Morning'),
        ('Afternoon', 'Afternoon'),
        ('Evening',   'Evening'),
    ]

    clinic       = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE,
                                     related_name='appointments')
    patient      = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                     related_name='appointments')
    receptionist = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='handled_appointments')
    doctor       = models.ForeignKey('doctors.Doctor', null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='appointments')
    clinic_name_snapshot = models.CharField(max_length=150, blank=True)

    # Patient's request
    condition_description = models.TextField()
    preferred_date        = models.DateField()
    preferred_time_of_day = models.CharField(max_length=20, choices=TIME_OF_DAY, default='Morning')

    # Receptionist's proposal to patient
    proposed_date      = models.DateField(null=True, blank=True)
    proposed_time_slot = models.TimeField(null=True, blank=True)
    proposal_message   = models.TextField(blank=True)
    proposal_sent_at   = models.DateTimeField(null=True, blank=True)
    patient_response   = models.CharField(
        max_length=20,
        choices=[('accepted', 'Accepted'), ('declined', 'Declined')],
        blank=True
    )
    patient_response_at = models.DateTimeField(null=True, blank=True)

    # After acceptance — confirmed slot
    confirmed_date      = models.DateField(null=True, blank=True)
    confirmed_time_slot = models.TimeField(null=True, blank=True)

    # Booking fee
    booking_fee          = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    booking_fee_currency = models.CharField(max_length=10, default='USD')

    rejection_note = models.TextField(blank=True)
    doctor_note    = models.TextField(blank=True)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES,
                               default='pending', db_index=True)

    requested_at  = models.DateTimeField(default=timezone.now)
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'appointments'
        indexes  = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['patient']),
            models.Index(fields=['doctor', 'confirmed_date']),
        ]

    def __str__(self):
        return f'Appt #{self.pk} — {self.patient} @ {self.clinic}'

    @property
    def status_color(self):
        return {
            'pending':           'warning',
            'proposed':          'info',
            'accepted':          'info',
            'awaiting_payment':  'warning',
            'payment_submitted': 'primary',
            'confirmed':         'success',
            'completed':         'secondary',
            'cancelled':         'danger',
            'no_show':           'purple',
        }.get(self.status, 'secondary')

    @property
    def display_date(self):
        return self.confirmed_date or self.proposed_date or self.preferred_date

    @property
    def display_time(self):
        return self.confirmed_time_slot or self.proposed_time_slot


class AppointmentPayment(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]
    METHOD_CHOICES = [
    ('card',          '💳 Credit / Debit Card (Visa, Mastercard, Amex)'),
    ('mtn_momo',      '📱 MTN Mobile Money'),
    ('mpesa',         '📱 M-Pesa'),
    ('airtel_money',  '📱 Airtel Money'),
    ('orange_money',  '📱 Orange Money'),
    ('tigo_pesa',     '📱 Tigo Pesa'),
    ('bank_transfer', '🏦 Bank Transfer'),
    ('paypal',        '🅿️ PayPal'),
    ('cash',          '💵 Cash (pay at clinic)'),
    ('other',         '🔄 Other'),
]

    appointment    = models.OneToOneField(Appointment, on_delete=models.CASCADE,
                                          related_name='payment')
    amount         = models.DecimalField(max_digits=10, decimal_places=2)
    currency       = models.CharField(max_length=10, default='USD')
    method         = models.CharField(max_length=20, choices=METHOD_CHOICES)
    reference      = models.CharField(max_length=200, blank=True)
    proof_of_payment = models.FileField(
        upload_to='payment_proofs/', null=True, blank=True
    )
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes          = models.TextField(blank=True)
    paid_at        = models.DateTimeField(null=True, blank=True)
    verified_at    = models.DateTimeField(null=True, blank=True)
    verified_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='verified_payments'
    )
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'appointment_payments'

    def __str__(self):
        return f'Payment #{self.pk} for Appt #{self.appointment_id}'