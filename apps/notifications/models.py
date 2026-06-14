from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    TYPE_CHOICES = [
        ('appointment', 'Appointment Update'),
        ('payment',     'Payment'),
        ('report',      'Medical Report'),
        ('approval',    'Account/Clinic Approval'),
        ('system',      'System'),
        ('message',     'Message'),
    ]
    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                    related_name='notifications')
    type       = models.CharField(max_length=20, choices=TYPE_CHOICES, default='system')
    title      = models.CharField(max_length=200)
    message    = models.TextField()
    link       = models.CharField(max_length=300, blank=True)
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.title}'