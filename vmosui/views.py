import fcntl
import json
import logging
import yaml

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponse
from django.shortcuts import render, redirect

from vmosui.forms import VCenterForm
from vmosui.utils import getters


LOG = logging.getLogger(__name__)


def index(request):
    """Main page, where the magic happens."""
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        containers = yaml.load(fp)
        fcntl.flock(fp, fcntl.LOCK_UN)
    
    return render(request, 'vmosui/index.html', {
        'containers': containers,
        'vcenter_form': VCenterForm(),
    })


def login(request):
    """Login form for authenticating user/password."""
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
    """Remove user's authenticated status."""
    username = request.user.username
    auth.logout(request)
    LOG.info('User %s logged out' % username)
    # Go back to home page
    return login(request)


def list_options(request):
    """Get options for a given field."""
    field_id = request.REQUEST.get('fid')
    fn_name = 'get_%ss' % field_id  # Getter names are in plural form
    fn = getattr(getters, fn_name)

    kwargs = {
        'vcenter': request.REQUEST.get('vcenter'),
        'username': request.REQUEST.get('username'), 
        'password': request.REQUEST.get('password')
    }
    datacenter = request.REQUEST.get('datacenter')
    if datacenter is not None:
        kwargs['datacenter'] = datacenter
    cluster = request.REQUEST.get('cluster')
    if cluster is not None:
        kwargs['cluster'] = cluster
    options = fn(**kwargs)

    data = {}
    if options is not None:
        opt_names = options.keys()
        opt_names.sort()
        data['options'] = opt_names
    else:
        data['error_message'] = 'Invalid username or password.'
    return HttpResponse(json.dumps(data), content_type='application/json')


def save_vcenter(request):
    """Save entered vCenter settings."""
    form = VCenterForm(request.POST)
    data = {}

    if form.is_valid():
        comp_vc = form.cleaned_data[getters.COMP_VC]
        comp_vc_username = form.cleaned_data[getters.COMP_VC_USERNAME]
        comp_vc_password = form.cleaned_data[getters.COMP_VC_PASSWORD]
        comp_vc_datacenter = form.cleaned_data[getters.COMP_VC_DATACENTER]
        comp_vc_cluster = form.cleaned_data[getters.COMP_VC_CLUSTER]

        mgmt_vc = form.cleaned_data[getters.MGMT_VC]
        mgmt_vc_username = form.cleaned_data[getters.MGMT_VC_USERNAME]
        mgmt_vc_password = form.cleaned_data[getters.MGMT_VC_PASSWORD]
        mgmt_vc_datacenter = form.cleaned_data[getters.MGMT_VC_DATACENTER]
        mgmt_vc_cluster = form.cleaned_data[getters.MGMT_VC_CLUSTER]

        # Cast unicode values as strings.
        vcenter_data = {
            getters.COMP_VC: str(comp_vc),
            getters.COMP_VC_USERNAME: str(comp_vc_username),
            getters.COMP_VC_PASSWORD: str(comp_vc_password),
            getters.COMP_VC_DATACENTER: str(comp_vc_datacenter),
            getters.COMP_VC_CLUSTER: str(comp_vc_cluster),
            getters.MGMT_VC: str(mgmt_vc),
            getters.MGMT_VC_USERNAME: str(mgmt_vc_username),
            getters.MGMT_VC_PASSWORD: str(mgmt_vc_password),
            getters.MGMT_VC_DATACENTER: str(mgmt_vc_datacenter),
            getters.MGMT_VC_CLUSTER: str(mgmt_vc_cluster),
        }

        # Save to file.
        filename = settings.VCENTER_SETTINGS
        with open(filename, 'w+') as fp:
            fcntl.flock(fp, fcntl.LOCK_EX)
            fp.write(yaml.dump(vcenter_data, default_flow_style=False))
            fcntl.flock(fp, fcntl.LOCK_UN)
            LOG.debug('vCenter data file %s written' % filename)
    else:
        LOG.error('Unable to save vCenter settings: %s' % form.errors)
        data['errors'] = form.errors
    return HttpResponse(json.dumps(data), content_type='application/json')
