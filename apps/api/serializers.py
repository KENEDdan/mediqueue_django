from rest_framework import serializers
from apps.clinics.models import Clinic, Specialization
from apps.appointments.models import Appointment
from apps.doctors.models import Doctor


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Specialization
        fields = ['id', 'name', 'icon', 'description']


class ClinicSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Clinic
        fields = ['id', 'name', 'slug', 'address', 'city', 'country',
                  'phone', 'email', 'latitude', 'longitude']


class DoctorSerializer(serializers.ModelSerializer):
    full_name      = serializers.CharField(source='user.full_name')
    specialization = serializers.CharField(source='specialization.name',
                                            allow_null=True)

    class Meta:
        model  = Doctor
        fields = ['id', 'full_name', 'specialization', 'bio',
                  'experience_years', 'is_accepting_patients']


class AppointmentSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)

    class Meta:
        model  = Appointment
        fields = ['id', 'clinic_name', 'condition_description',
                  'preferred_date', 'status', 'requested_at']