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
# From http://stackoverflow.com/questions/10031001/login-required-decorator-on-ajax-views-to-return-401-instead-of-302.
#
from django.http import HttpResponse


def login_required_ajax(function=None):
    """
    Make sure the user is authenticated to access a certain AJAX view.

    If not, return a HttpResponse 401 - authentication required - instead of
    the 302 redirect of the original Django decorator.
    """
    def _decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated():
                return view_func(request, *args, **kwargs)
            else:
                return HttpResponse(status=401)
        return _wrapped_view

    if function is None:
        return _decorator
    else:
        return _decorator(function)
