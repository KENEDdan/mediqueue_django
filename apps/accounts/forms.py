from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.conf import settings
from .models import User


class PatientLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'placeholder': 'you@example.com', 'autofocus': True})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )


class StaffLoginForm(forms.Form):
    email = forms.EmailField(
        label='Email Address',
        widget=forms.EmailInput(attrs={'placeholder': 'your.name@clinic.mediqueue'})
    )
    password = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )


class PatientRegisterForm(forms.ModelForm):
    password  = forms.CharField(label='Password', min_length=8,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 8 characters'}))
    password2 = forms.CharField(label='Confirm Password',
                                widget=forms.PasswordInput(attrs={'placeholder': 'Repeat your password'}))
    security_question = forms.ChoiceField(
        choices=[('', '— Select a question —')] + [(q, q) for q in settings.SECURITY_QUESTIONS]
    )

    class Meta:
        model  = User
        fields = ['full_name', 'email', 'phone', 'gender', 'date_of_birth',
                  'security_question', 'security_answer']
        widgets = {
            'full_name':     forms.TextInput(attrs={'placeholder': 'John Doe'}),
            'email':         forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'phone':         forms.TextInput(attrs={'placeholder': '+250 7XX XXX XXX'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'security_answer': forms.TextInput(attrs={'placeholder': 'Your answer'}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.role = 'patient'
        user.approval_status = 'approved'
        if commit:
            user.save()
        return user


class ForgotPasswordStep1Form(forms.Form):
    email = forms.EmailField(label='Email Address',
                             widget=forms.EmailInput(attrs={'placeholder': 'you@example.com'}))


class SecurityAnswerForm(forms.Form):
    answer = forms.CharField(label='Your Answer',
                             widget=forms.TextInput(attrs={'placeholder': 'Type your answer'}))


class ResetPasswordForm(forms.Form):
    password  = forms.CharField(label='New Password', min_length=8,
                                widget=forms.PasswordInput(attrs={'placeholder': 'Minimum 8 characters'}))
    password2 = forms.CharField(label='Confirm Password',
                                widget=forms.PasswordInput(attrs={'placeholder': 'Repeat new password'}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password2'):
            raise forms.ValidationError('Passwords do not match.')
        return cleaned