from core.models import User
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password


class EmailAuthBackend(BaseBackend):

    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return None

        if check_password(password, user.password_hash):
            return user

        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(user_id=user_id)  # ✅ FIXED
        except User.DoesNotExist:
            return None