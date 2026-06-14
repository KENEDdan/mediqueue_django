from django import forms
from django.conf import settings
from .models import Clinic, ClinicDocument, ClinicService, Specialization


class ClinicRegisterForm(forms.Form):
    # Clinic info
    clinic_name    = forms.CharField(max_length=150, label='Clinic / Hospital Name',
                                     widget=forms.TextInput(attrs={'placeholder': 'City Medical Centre'}))
    clinic_phone   = forms.CharField(max_length=30, label='Phone Number',
                                     widget=forms.TextInput(attrs={'placeholder': '+250 7XX XXX XXX'}))
    clinic_email   = forms.EmailField(label='Clinic Email',
                                      widget=forms.EmailInput(attrs={'placeholder': 'info@clinic.com'}))
    clinic_address = forms.CharField(label='Physical Address',
                                     widget=forms.TextInput(attrs={'placeholder': '123 Health St, Kigali'}))

    # Admin account
    admin_name     = forms.CharField(max_length=150, label='Your Full Name',
                                     widget=forms.TextInput(attrs={'placeholder': 'Jane Doe'}))
    admin_email    = forms.EmailField(label='Admin Email',
                                      widget=forms.EmailInput(attrs={'placeholder': 'admin@youremail.com'}))
    admin_password = forms.CharField(label='Password', min_length=8,
                                     widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 8 characters'}))

    # Security question
    security_question = forms.ChoiceField(
        label='Security Question',
        choices=[('', '— Select a question —')] + [(q, q) for q in settings.SECURITY_QUESTIONS]
    )
    security_answer = forms.CharField(label='Your Answer',
                                      widget=forms.TextInput(attrs={'placeholder': 'Answer to the question'}))

    # Subscription plan (required — no free plan)
    PLAN_CHOICES = [('', '— Choose a plan —')] + [
        (k, f"{v['icon']} {v['name']} — ${v['price_monthly']}/month")
        for k, v in settings.SUBSCRIPTION_PLANS.items()
    ]
    subscription_plan = forms.ChoiceField(choices=PLAN_CHOICES, label='Subscription Plan')

    # Billing cycle
    BILLING_CHOICES = [('monthly', 'Monthly'), ('annual', 'Annual (Save 17%)')]
    billing_cycle = forms.ChoiceField(choices=BILLING_CHOICES, label='Billing Cycle',
                                      widget=forms.RadioSelect)

    # Credit card (required for trial — no charge for 30 days)
    card_holder = forms.CharField(max_length=150, label='Cardholder Name',
                                  widget=forms.TextInput(attrs={'placeholder': 'Full name on card'}))
    card_number = forms.CharField(max_length=19, label='Card Number',
                                  widget=forms.TextInput(attrs={'placeholder': '1234 5678 9012 3456',
                                                                 'maxlength': '19'}))
    card_expiry = forms.CharField(max_length=5, label='Expiry Date',
                                  widget=forms.TextInput(attrs={'placeholder': 'MM/YY', 'maxlength': '5'}))
    card_cvv    = forms.CharField(max_length=4, label='CVV',
                                  widget=forms.PasswordInput(attrs={'placeholder': '•••', 'maxlength': '4'}))

    # Document uploads
    registration_cert = forms.FileField(
        label='Registration Certificate (PDF/JPG/PNG)',
        widget=forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        required=True,
        help_text='Required — your clinic/hospital registration certificate.'
    )
    medical_license = forms.FileField(
        label='Medical License (optional)',
        widget=forms.FileInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        required=False
    )

    def clean_card_number(self):
        num = self.cleaned_data['card_number'].replace(' ', '').replace('-', '')
        if not num.isdigit() or len(num) < 13:
            raise forms.ValidationError('Enter a valid card number.')
        return num

    def clean_card_cvv(self):
        cvv = self.cleaned_data['card_cvv']
        if not cvv.isdigit() or len(cvv) < 3:
            raise forms.ValidationError('Enter a valid CVV.')
        return cvv

    def clean_subscription_plan(self):
        plan = self.cleaned_data['subscription_plan']
        if not plan:
            raise forms.ValidationError('Please select a subscription plan.')
        return plan


class ClinicUpdateForm(forms.ModelForm):
    class Meta:
        model  = Clinic
        fields = ['name', 'phone', 'email', 'address', 'logo']
        widgets = {
            'name':    forms.TextInput(attrs={'class': 'form-control'}),
            'phone':   forms.TextInput(attrs={'class': 'form-control'}),
            'email':   forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
        }


class ClinicServiceForm(forms.ModelForm):
    class Meta:
        model  = ClinicService
        fields = ['specialization', 'description']
        widgets = {
            'specialization': forms.Select(attrs={'class': 'form-select'}),
            'description':    forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
        }