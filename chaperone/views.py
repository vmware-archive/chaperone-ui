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
import fcntl
import json
import logging
import os

from django.conf import settings
from django.contrib import auth
from django.http import HttpResponse
from django.shortcuts import render, redirect

from prepare.views import write_answer_file
from chaperone.forms import VCenterForm
from chaperone.utils import getters, yaml

LOG = logging.getLogger(__name__)

MIN_MGMT_NETWORKS = 1


def index(request):
    """Main page, where the magic happens."""
    filename = os.path.join(settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    menus = yaml.load(filename)

    return render(request, 'chaperone/index.html', {
        'menus': menus,
        'application_full_name': settings.APP_FULLNAME,
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
            filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                                  settings.ANSWER_FILE_DEFAULT)
            if not os.path.exists(filename):
                # Initialize answer file with default values.
                write_answer_file(request, filename)
            return redirect(request.REQUEST.get('next'))
        else:
            # Bad password, no donut.
            LOG.info('User %s made failed login attempt' % username)
            error_message = 'Invalid username or password.'

    return render(request, 'chaperone/login.html', {
        'error_message': error_message,
        'next_url': request.GET.get('next', '/'),
        'username': username,
        'application_full_name': settings.APP_FULLNAME,
        'application_short_name': settings.APP_SHORTNAME,
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
    fn_name = 'get_%s' % field_id
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
        data['errors'] = ['Invalid username or password.']
    return HttpResponse(json.dumps(data), content_type='application/json')


def vcenter_settings(request):
    """Main page, where the magic happens."""
    filename = os.path.join(settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    menus = yaml.load(filename)

    try:
        vcenter_form = VCenterForm()
    except Exception, msg:
        LOG.warn("Exception ocured attempting to connect with vCenter: %s" % msg)
        vcenter_form = []

    missing_values = False
    for field in vcenter_form:
        if not field.field.initial:
            missing_values = True
            break

    return render(request, 'chaperone/vcenter.html', {
        'menus': menus,
        'vcenter_form': vcenter_form,
        'missing_values': missing_values,
        'application_full_name': settings.APP_FULLNAME,
    })


def save_vcenter(request):
    """Save entered vCenter settings."""
    try:
        form = VCenterForm(request.POST)
    except:
		form = None
    data = {}

    if form and form.is_valid():
        errors = []

        comp_vc = str(form.cleaned_data[getters.COMP_VC])
        comp_vc_username = str(form.cleaned_data[getters.COMP_VC_USERNAME])
        comp_vc_password = str(form.cleaned_data[getters.COMP_VC_PASSWORD])
        comp_vc_datacenter = str(form.cleaned_data[getters.COMP_VC_DATACENTER])
        comp_vc_cluster = str(form.cleaned_data[getters.COMP_VC_CLUSTER])

        mgmt_vc = str(form.cleaned_data[getters.MGMT_VC])
        mgmt_vc_username = str(form.cleaned_data[getters.MGMT_VC_USERNAME])
        mgmt_vc_password = str(form.cleaned_data[getters.MGMT_VC_PASSWORD])
        mgmt_vc_datacenter = str(form.cleaned_data[getters.MGMT_VC_DATACENTER])
        mgmt_vc_cluster = str(form.cleaned_data[getters.MGMT_VC_CLUSTER])

        vcenter_data = {
            getters.COMP_VC: comp_vc,
            getters.COMP_VC_USERNAME: comp_vc_username,
            getters.COMP_VC_PASSWORD: comp_vc_password,
            getters.COMP_VC_DATACENTER: comp_vc_datacenter,
            getters.COMP_VC_CLUSTER: comp_vc_cluster,
            getters.MGMT_VC: mgmt_vc,
            getters.MGMT_VC_USERNAME: mgmt_vc_username,
            getters.MGMT_VC_PASSWORD: mgmt_vc_password,
            getters.MGMT_VC_DATACENTER: mgmt_vc_datacenter,
            getters.MGMT_VC_CLUSTER: mgmt_vc_cluster,
        }

        # Save vCenter settings to file.
        yaml.dump(settings.VCENTER_SETTINGS, vcenter_data, default_flow_style=False)

        options_data = {
            getters.COMP_VC: [comp_vc],
            getters.COMP_VC_USERNAME: [comp_vc_username],
            getters.COMP_VC_PASSWORD: [comp_vc_password],
            getters.MGMT_VC: [mgmt_vc],
            getters.MGMT_VC_USERNAME: [mgmt_vc_username],
            getters.MGMT_VC_PASSWORD: [mgmt_vc_password],
        }

        # Get management datacenters.
        mgmt_vc_datacenters = getters.get_mgmt_vc_datacenter(
            vcenter=mgmt_vc, username=mgmt_vc_username,
            password=mgmt_vc_password, datacenter='')
        if not mgmt_vc_datacenters:
            errors.append('No management vCenter datacenters found.')
        else:
            options_data[getters.MGMT_VC_DATACENTER] = (
                mgmt_vc_datacenters.keys())

        # Get clusters in the management datacenters.
        mgmt_vc_clusters = None
        if mgmt_vc_datacenters:
            mgmt_vc_clusters = getters.get_mgmt_vc_cluster(
                vcenter=mgmt_vc, username=mgmt_vc_username,
                password=mgmt_vc_password, datacenter=mgmt_vc_datacenter,
                cluster='')
            if not mgmt_vc_clusters:
                errors.append('No management vCenter clusters found.')
            else:
                options_data[getters.MGMT_VC_CLUSTER] = mgmt_vc_clusters.keys()

        if mgmt_vc_clusters:
            # Get hosts in these clusters.
            mgmt_vc_hosts = getters.get_mgmt_vc_hosts(
                vcenter=mgmt_vc, username=mgmt_vc_username,
                password=mgmt_vc_password, datacenter=mgmt_vc_datacenter,
                cluster=mgmt_vc_cluster)
            if not mgmt_vc_hosts:
                errors.append('No management vCenter hosts found.')
            else:
                options_data[getters.MGMT_VC_HOSTS] = mgmt_vc_hosts.keys()

            # Get datastores in these clusters.
            mgmt_vc_datastores = getters.get_mgmt_vc_datastores(
                vcenter=mgmt_vc, username=mgmt_vc_username,
                password=mgmt_vc_password, datacenter=mgmt_vc_datacenter,
                cluster=mgmt_vc_cluster)
            if not mgmt_vc_datastores:
                errors.append('No management vCenter datastores found.')
            else:
                options_data[getters.MGMT_VC_DATASTORES] = mgmt_vc_datastores.keys()

            # Get networks in these clusters.
            mgmt_vc_networks = getters.get_mgmt_vc_networks(
                vcenter=mgmt_vc, username=mgmt_vc_username,
                password=mgmt_vc_password, datacenter=mgmt_vc_datacenter,
                cluster=mgmt_vc_cluster)
            if (not mgmt_vc_networks or
                    len(mgmt_vc_networks) < MIN_MGMT_NETWORKS):
                errors.append(
                    'At least %s management vCenter network%s must be '
                    'available.' % (MIN_MGMT_NETWORKS,
                                    '' if MIN_MGMT_NETWORKS == 1 else 's'))
            else:
                options_data[getters.MGMT_VC_NETWORKS] = mgmt_vc_networks.keys()

        # Get compute datacenters.
        comp_vc_datacenters = getters.get_comp_vc_datacenter(
            vcenter=comp_vc, username=comp_vc_username,
            password=comp_vc_password, datacenter='')
        if not comp_vc_datacenters:
            errors.append('No compute vCenter datacenters found.')
        else:
            options_data[getters.COMP_VC_DATACENTER] = (
                comp_vc_datacenters.keys())

        # Get clusters in the compute datacenters.
        comp_vc_clusters = None
        if comp_vc_datacenters:
            comp_vc_clusters = getters.get_comp_vc_cluster(
                vcenter=comp_vc, username=comp_vc_username,
                password=comp_vc_password, datacenter=comp_vc_datacenter,
                cluster='')
            if not comp_vc_clusters:
                errors.append('No compute vCenter clusters found.')
            else:
                options_data[getters.COMP_VC_CLUSTER] = comp_vc_clusters.keys()

        if comp_vc_clusters:
            # Get hosts in these clusters.
            comp_vc_hosts = getters.get_comp_vc_hosts(
                vcenter=comp_vc, username=comp_vc_username,
                password=comp_vc_password, datacenter=comp_vc_datacenter,
                cluster=comp_vc_cluster)
            if not comp_vc_hosts:
                errors.append('No compute vCenter hosts found.')
            else:
                options_data[getters.COMP_VC_HOSTS] = comp_vc_hosts.keys()

            # Get datastores in these clusters.
            comp_vc_datastores = getters.get_comp_vc_datastores(
                vcenter=comp_vc, username=comp_vc_username,
                password=comp_vc_password, datacenter=comp_vc_datacenter,
                cluster=comp_vc_cluster)
            if not comp_vc_datastores:
                errors.append('No compute vCenter datastores found.')
            else:
                options_data[getters.COMP_VC_DATASTORES] = comp_vc_datastores.keys()

            # Get networks in these clusters.
            comp_vc_networks = getters.get_comp_vc_networks(
                vcenter=comp_vc, username=comp_vc_username,
                password=comp_vc_password, datacenter=comp_vc_datacenter,
                cluster=comp_vc_cluster)
            options_data[getters.COMP_VC_NETWORKS] = comp_vc_networks.keys()

        if errors:
            LOG.error('Unable to save vCenter settings: %s' % errors)
            data['errors'] = errors
        else:
            # Save vCenter field options to file.
            options_filename = settings.INPUT_OPTIONS
            yaml.dump(options_filename, options_data, default_flow_style=False)

            # Rewrite the answer file, to update with new vCenter values and
            # check if previously saved values for dynamically populated fields
            # are no longer valid.
            base_filename = os.path.join(settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
            menus = yaml.load(base_filename)

            containers = []
            for menu in menus:
                for menu_name, menu_containers in menu.items():
                    if menu_name == settings.PREPARE_MENU:
                        containers = menu_containers
                        break

            new_answers = {}
            values_cache = {}
            # [{ ... }]
            for container in containers:
                # { 'Container': { ... } }
                for groups in container.values():
                    # [{ ... }]
                    for group in groups:
                        # { 'Group': [...] }
                        for sections in group.values():
                            # [{ ... }]
                            for section in sections:
                                # { 'Section': [...] }
                                for attributes in section.values():
                                    # [{ ... }]
                                    for attr in attributes:
                                        attr_id = attr['id']
                                        opts = attr.get('options', [])
                                        if not isinstance(opts, list):
                                            if opts not in vcenter_data:
                                                break
                                            if opts in values_cache:
                                                new_answers[attr_id] = (
                                                    values_cache[attr_id])
                                            else:
                                                fn_name = 'get_%s_value' % opts
                                                fn = getattr(getters, fn_name)
                                                value = fn()
                                                new_answers[attr_id] = value
                                                values_cache[attr_id] = value

            LOG.debug('New vCenter settings answers: %s' % new_answers)
            answers_filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                                          settings.ANSWER_FILE_DEFAULT)
            write_answer_file(request, answers_filename,
                              new_answers=new_answers)
    else:
        if form is not None:
            LOG.error('Unable to save vCenter settings: %s' % form.errors)
            data['field_errors'] = form.errors
        else:
            LOG.error('Unable to save vCenter settings: no vCenter form exists!')
            data['field_errors'] = 'No form was created'
    return HttpResponse(json.dumps(data), content_type='application/json')
