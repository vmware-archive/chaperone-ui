from django.contrib.auth.models import User

from utils import pam


class PamBackend(object):
    def authenticate(self, username=None, password=None):
        # Check the username/password and record the username.
        if pam.authenticate(username, password, service='login'):
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                # Create a new user. Don't bother storing the real password.
                user = User(username=username, password='X', is_active=True)
                user.save()
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
