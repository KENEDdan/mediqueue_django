from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class MediQueueAuthBackend:
    """
    Authenticates by email OR generated_email.
    Clinic staff log in with their generated email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or '').strip().lower()
        try:
            user = User.objects.get(Q(email=email) | Q(generated_email=email))
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        return getattr(user, 'is_active', False)

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None