import fcntl
import logging
import yaml

from django.conf import settings
from django.contrib import auth
from django.shortcuts import render, redirect


LOG = logging.getLogger(__name__)


def index(request):
    """ Main page, where the magic happens. """
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        containers = yaml.load(fp)
        fcntl.flock(fp, fcntl.LOCK_UN)
    
    return render(request, 'vmosui/index.html', {
        'containers': containers,
    })


def login(request):
    """ Login form for authenticating user/password. """
    username = request.REQUEST.get('username', '')
    password = request.REQUEST.get('password')
    error_message = ''

    if username and password:
        user = auth.authenticate(username=username, password=password)
        if user is not None:
            # Success.
            auth.login(request, user)
            LOG.info('User %s logged in' % username)
            return redirect(request.REQUEST.get('next'))
        else:
            # Bad password, no donut.
            LOG.info('User %s made failed login attempt' % username)
            error_message = 'Invalid username or password.'

    return render(request, 'vmosui/login.html', {
        'error_message': error_message,
        'next_url': request.GET.get('next', '/'),
        'username': username,
    })


def logout(request):
    """ Remove user's authenticated status. """
    username = request.user.username
    auth.logout(request)
    LOG.info('User %s logged out' % username)
    # Go back to home page
    return login(request)
