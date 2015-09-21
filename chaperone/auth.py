#
#  Copyright 2015 VMware, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
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
