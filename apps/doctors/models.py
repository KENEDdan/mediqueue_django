from django.db import models
from django.conf import settings


class Doctor(models.Model):
    user                = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doctor')
    clinic              = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='doctors')
    specialization      = models.ForeignKey('clinics.Specialization', on_delete=models.PROTECT)
    license_number      = models.CharField(max_length=100, blank=True)
    bio                 = models.TextField(blank=True)
    slot_duration_mins  = models.IntegerField(default=30)
    max_patients_per_day = models.IntegerField(default=20)
    is_accepting_patients = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'doctors'

    def __str__(self):
        return f'Dr. {self.user.full_name}'


class DoctorSchedule(models.Model):
    DAY_CHOICES = [(i, day) for i, day in enumerate(
        ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    )]
    doctor      = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time  = models.TimeField()
    end_time    = models.TimeField()
    is_active   = models.BooleanField(default=True)

    class Meta:
        db_table = 'doctor_schedules'
        unique_together = ('doctor', 'day_of_week')

    def __str__(self):
        return f'{self.doctor} — {self.get_day_of_week_display()}'


class DoctorBlockedDate(models.Model):
    doctor       = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='blocked_dates')
    blocked_date = models.DateField()
    reason       = models.CharField(max_length=255, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'doctor_blocked_dates'
        unique_together = ('doctor', 'blocked_date')

    def __str__(self):
        return f'{self.doctor} — {self.blocked_date}'