import re
import secrets
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra):
        if not email:
            raise ValueError('Email required')
        email = self.normalize_email(email)
        user  = self.model(email=email, full_name=full_name, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra):
        extra.setdefault('role', 'super_admin')
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('approval_status', 'approved')
        return self.create_user(email, full_name, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('super_admin',  'Super Admin'),
        ('clinic_admin', 'Clinic Admin'),
        ('receptionist', 'Receptionist'),
        ('doctor',       'Doctor'),
        ('patient',      'Patient'),
    ]
    GENDER_CHOICES   = [('Male','Male'),('Female','Female'),('Other','Other')]
    APPROVAL_CHOICES = [('approved','Approved'),('pending','Pending'),('rejected','Rejected')]
    REG_TYPE_CHOICES = [('admin_created','Admin Created'),('self_registered','Self Registered')]

    clinic          = models.ForeignKey(
        'clinics.Clinic', null=True, blank=True,
        on_delete=models.SET_NULL, related_name='staff'
    )
    full_name       = models.CharField(max_length=150)
    email           = models.EmailField(unique=True, db_index=True)
    generated_email = models.CharField(max_length=150, blank=True, db_index=True)
    phone           = models.CharField(max_length=30, blank=True)
    role            = models.CharField(max_length=20, choices=ROLE_CHOICES, default='patient', db_index=True)
    gender          = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    date_of_birth   = models.DateField(null=True, blank=True)
    address         = models.TextField(blank=True)
    profile_photo   = models.ImageField(upload_to='profiles/', null=True, blank=True)
    security_question = models.CharField(max_length=255, blank=True)
    security_answer   = models.CharField(max_length=255, blank=True)
    email_verified      = models.BooleanField(default=False)
    email_verify_token  = models.CharField(max_length=64, blank=True)
    email_token_expires = models.DateTimeField(null=True, blank=True)
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_CHOICES, default='approved')
    registration_type = models.CharField(max_length=20, choices=REG_TYPE_CHOICES, default='self_registered')
    created_at      = models.DateTimeField(default=timezone.now)
    referral_code   = models.CharField(max_length=12, unique=True, blank=True)
    referred_by     = models.ForeignKey('self', null=True, blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='referrals')
    referral_credits = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        db_table = 'users'

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = secrets.token_urlsafe(8).upper()[:8]
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.full_name} ({self.role})'

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ''

    @property
    def display_email(self):
        return self.generated_email or self.email

    def is_clinic_staff(self):
        return self.role in ('clinic_admin', 'receptionist', 'doctor')

    @staticmethod
    def generate_staff_email(full_name: str, clinic_slug: str) -> str:
        parts = full_name.strip().lower().split()
        base  = f'{parts[0]}.{parts[-1]}' if len(parts) >= 2 else parts[0]
        base  = re.sub(r'[^a-z0-9.]', '', base)
        email = f'{base}@{clinic_slug}.mediqueue'
        counter = 2
        candidate = email
        while User.objects.filter(
            models.Q(email=candidate) | models.Q(generated_email=candidate)
        ).exists():
            candidate = f'{base}{counter}@{clinic_slug}.mediqueue'
            counter  += 1
        return candidate