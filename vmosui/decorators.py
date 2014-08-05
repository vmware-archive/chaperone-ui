# From http://stackoverflow.com/questions/10031001/login-required-decorator-on-ajax-views-to-return-401-instead-of-302.
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
