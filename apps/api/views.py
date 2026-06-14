from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.clinics.models import Clinic, Specialization
from apps.appointments.models import Appointment
from .serializers import (ClinicSerializer, SpecializationSerializer,
                           AppointmentSerializer)


class ClinicListAPI(generics.ListAPIView):
    serializer_class   = ClinicSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Clinic.objects.filter(
            approval_status='approved', is_active=True
        ).order_by('name')[:50]


class SpecializationListAPI(generics.ListAPIView):
    serializer_class   = SpecializationSerializer
    permission_classes = [AllowAny]
    queryset           = Specialization.objects.all().order_by('name')


class PatientAppointmentsAPI(generics.ListAPIView):
    serializer_class   = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Appointment.objects.filter(
            patient=self.request.user
        ).select_related('clinic').order_by('-requested_at')


@api_view(['GET'])
@permission_classes([AllowAny])
def available_slots_api(request):
    from apps.appointments.views import _get_available_slots
    from apps.doctors.models import Doctor
    doctor_id = request.query_params.get('doctor_id')
    date_str  = request.query_params.get('date')
    if not doctor_id or not date_str:
        return Response({'error': 'doctor_id and date required.'}, status=400)
    try:
        doctor = Doctor.objects.get(pk=doctor_id)
        slots  = _get_available_slots(doctor, date_str)
        return Response({'slots': slots})
    except Doctor.DoesNotExist:
        return Response({'slots': [], 'error': 'Doctor not found.'}, status=404)