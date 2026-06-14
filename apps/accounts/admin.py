from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['full_name', 'email', 'role', 'is_active', 'approval_status', 'created_at']
    list_filter   = ['role', 'is_active', 'approval_status']
    search_fields = ['full_name', 'email', 'generated_email']
    ordering      = ['-created_at']
    fieldsets     = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('full_name', 'phone', 'gender', 'date_of_birth', 'address')}),
        ('MediQueue', {'fields': ('role', 'clinic', 'generated_email', 'approval_status',
                                   'registration_type', 'security_question', 'security_answer')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = ((None, {'fields': ('email', 'full_name', 'role', 'password1', 'password2')}),)