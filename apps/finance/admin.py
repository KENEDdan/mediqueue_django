from django.contrib import admin
from .models import PlatformSubscriptionPayment, ClinicPayoutAccount, ClinicTransaction

@admin.register(PlatformSubscriptionPayment)
class PlatformSubPaymentAdmin(admin.ModelAdmin):
    list_display  = ['clinic', 'plan', 'amount', 'status', 'paid_at']
    list_filter   = ['status', 'plan', 'billing_cycle']
    search_fields = ['clinic__name']
    readonly_fields = ['reference']

@admin.register(ClinicPayoutAccount)
class ClinicPayoutAccountAdmin(admin.ModelAdmin):
    list_display  = ['clinic', 'method', 'account_name', 'is_active']
    list_filter   = ['method', 'is_active']

@admin.register(ClinicTransaction)
class ClinicTransactionAdmin(admin.ModelAdmin):
    list_display  = ['clinic', 'patient_display', 'amount', 'method', 'status', 'paid_at']
    list_filter   = ['status', 'clinic', 'method']
    readonly_fields = ['reference']