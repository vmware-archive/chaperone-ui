import fcntl
import json
import logging
import os
import re
import subprocess
import time

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render


LOG = logging.getLogger(__name__)

ACTION_RUN = 'run'
HV_COUNT_COOKIE = 'hvcount'
HV_TEMPLATE = """%s ansible_ssh_user="%s" ansible_ssh_pass="%s" bond_mode="%s" nic="[%s]" transport_ip="%s" transport_mask="%s" transport_gateway="%s"
"""
HV_HOST = 'host'
HV_USER = 'user'
HV_PASSWORD = 'password'
HV_BOND = 'bond'
HV_NICS = 'nics'
HV_TXIP = 'txip'
HV_TXMASK = 'txmask'
HV_TXGW = 'txgw'


def _index(request, logname, configure_type):
    # Show knobs to start running the configuration commands.
    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            fcntl.flock(lp, fcntl.LOCK_SH)
            file_contents = lp.read()
            fcntl.flock(lp, fcntl.LOCK_UN)

    return render(request, 'configure/_run.html', {
        'configure_type': configure_type,
        'log_contents': file_contents,
    })


def nsx_index(request):
    """ Display start page for NSX configuration commands. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.NSX_CONFIGURE_LOG)
    return _index(request, logname, 'nsx')


def sddc_index(request):
    """ Display start page for SDDC configuartion commands. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.SDDC_CONFIGURE_LOG)
    return _index(request, logname, 'sddc')


def hypervisors_index(request):
    """ Display form to configure hypervisors. """
    # Get hypervisors last configured.
    file_contents = []
    if os.path.exists(settings.HVS_INI):
        with open(settings.HVS_INI, 'r') as fp:
            fcntl.flock(fp, fcntl.LOCK_SH)
            file_contents = fp.readlines()
            fcntl.flock(fp, fcntl.LOCK_UN)

    first_line = True
    count = 0
    hvs = []
    for line in file_contents:
        if first_line:
            # Skip section name.
            first_line = False
            continue
        count += 1

        # Get values, based on HV_TEMPLATE format.
        args = line.split()
        hv = { 'count': count }
        host = args[0] 

        hv[HV_HOST] = host
        user = args[1].split('=')[-1].strip('"')
        hv[HV_USER] = user
        password = args[2].split('=')[-1].strip('"')
        hv[HV_PASSWORD] = password

        hv[HV_BOND] = args[3].split('=')[-1].strip('"')
        nics = re.findall(r"'.+?'", args[4].split('=')[-1].strip('"'))
        # Ignore surrounding single quotation marks.
        hv[HV_NICS] = ','.join([n.strip("'") for n in nics])

        hv[HV_TXIP] = args[5].split('=')[-1].strip('"')
        hv[HV_TXMASK] = args[6].split('=')[-1].strip('"')
        hv[HV_TXGW] = args[7].split('=')[-1].strip('"')
        hvs.append(hv)

    # Show knobs to start running the configuration commands.
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.HVS_CONFIGURE_LOG)
    log_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            fcntl.flock(lp, fcntl.LOCK_SH)
            log_contents = lp.read()
            fcntl.flock(lp, fcntl.LOCK_UN)

    response = render(request, 'configure/_hvs.html', {
        'count': count,
        'hvs': hvs,
        'log_contents': log_contents,
    });
    # Initialize cookie value.
    response.set_cookie(HV_COUNT_COOKIE, count)
    return response


def _run_commands(request, logname, commands):
    # Run the given commands, using any needed options from the request. The
    # commands must be given as a list, one string per command plus its
    # arguments and options.
    with open(logname, 'w+') as lp:
        num_cmds = len(commands)
        for i in xrange(0, num_cmds):
            cmd = commands[i]
            if request.REQUEST.get('debug') == '1':
                cmd = '%s %s' % (cmd, settings.DEBUG_OPTION)

            # Set Python output to be unbuffered so any output is returned
            # immediately.
            env = os.environ
            env['PYTHONUNBUFFERED'] = '1'
            LOG.info('Running "%s"' % cmd)
            proc = subprocess.Popen(cmd.split(), stdout=lp, stderr=lp, env=env)
            # Wait for each process to finish except for the last one, in case
            # later commands have dependencies on earlier ones.
            if not i == num_cmds -1:
                proc.wait()


def run_nsx_commands(request):
    """ Run configuration commands for NSX. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.NSX_CONFIGURE_LOG)
    if request.REQUEST.get('action') == ACTION_RUN:
        commands = settings.NSX_CONFIGURE_RUN
    else:
        commands = settings.NSX_CONFIGURE_VALIDATE

    _run_commands(request, logname, commands)
    # AJAX polling will check for output.
    return HttpResponse('')


def run_sddc_commands(request):
    """ Run configuration commands for SDDC. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.SDDC_CONFIGURE_LOG)
    if request.REQUEST.get('action') == ACTION_RUN:
        commands = settings.SDDC_CONFIGURE_RUN
    else:
        commands = settings.SDDC_CONFIGURE_VALIDATE

    _run_commands(request, logname, commands)
    # AJAX polling will check for output.
    return HttpResponse('')


def run_hvs_commands(request):
    """ Run configuration commands for SDDC. """
    # Build dictionary of hypervisors.
    # { 1: { ... }, 2: { ... }, ... }
    hvs = {}
    for key, value in request.REQUEST.iteritems():
        if not key.startswith('hv-'):
            continue

        # Get host number and argument name.
        data = key.split('-')
        num = data[-1]
        hv = hvs.setdefault(num, {})
        arg = data[-2]
        if arg == HV_NICS:
            value = request.REQUEST.getlist(key)
        hv[arg] = value
        LOG.debug('hv[%s] = %s' % (arg, value))

    # Write out all the input values into the init file.
    with open(settings.HVS_INI, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write('[hypervisors]\n')
        for hv in hvs.values():
            nics = ["'%s'" % n for n in hv.get(HV_NICS, [])]
            fp.write(HV_TEMPLATE % (hv.get(HV_HOST, ''), hv.get(HV_USER, ''),
                                    hv.get(HV_PASSWORD, ''),
                                    hv.get(HV_BOND, ''), ','.join(nics),
                                    hv.get(HV_TXIP, ''), hv.get(HV_TXMASK, ''),
                                    hv.get(HV_TXGW, '')))
        fcntl.flock(fp, fcntl.LOCK_UN)

    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.HVS_CONFIGURE_LOG)
    if request.REQUEST.get('action') == ACTION_RUN:
        commands = settings.HVS_CONFIGURE_RUN
    else:
        commands = settings.HVS_CONFIGURE_VALIDATE

    _run_commands(request, logname, commands)
    # AJAX polling will check for output.
    return HttpResponse('')


def _tail_log(request, logname):
    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            # Read what has been written to the file so far.
            fcntl.flock(lp, fcntl.LOCK_SH)
            file_contents = lp.read()
            fcntl.flock(lp, fcntl.LOCK_UN)
    return HttpResponse(file_contents, content_type='text/plain')


def tail_nsx_log(request):
    """ Return output written to the NSX log, since the last call to this. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.NSX_CONFIGURE_LOG)
    return _tail_log(request, logname)


def tail_sddc_log(request):
    """ Return output written to the SDDC log, since the last call to this. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.SDDC_CONFIGURE_LOG)
    return _tail_log(request, logname)


def tail_hvs_log(request):
    """ Return output written to the hypervisors log, since the last call to
    this.
    """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.HVS_CONFIGURE_LOG)
    return _tail_log(request, logname)


def get_nics(request):
    """ Return list of NICs on the given hypervisor. """
    host = request.REQUEST.get('host')
    user = request.REQUEST.get('user')
    password = request.REQUEST.get('password')

    filename = '%s/nics.ini' % settings.ANSWER_FILE_DIR
    with open(filename, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write('[getnics]\n')
        # Need to quote argument values, to escape special characters.
        fp.write("'%s' ansible_ssh_user='%s' ansible_ssh_pass='%s'\n" %
                 (host, user, password))
        fcntl.flock(fp, fcntl.LOCK_UN)

    data = { 'nics': [] }
    try:
        command = 'ansible-playbook -i %s/nics.ini %s' % (
            settings.ANSWER_FILE_DIR, settings.NICS_PLAYBOOK)
        LOG.info('Running "%s"' % command)
        output = subprocess.check_output(command.split())
    except subprocess.CalledProcessError as e:
        # Use first sentence of "fatal" string as error message.
        matches = re.search(r'^fatal: \[.+\] => (?P<error>.+)$', e.output,
                            re.MULTILINE)
        if matches:
            data['error'] = matches.group('error').split('.')[0]
        else:
            data['error'] = 'Unable to get NICs'
    else:
        # Parse NIC names from output.
        nics = list(set(re.findall(r'(vmnic[0-9]+)', output)))
        nics.sort()
        data['nics'] = nics
    return HttpResponse(json.dumps(data), content_type='application/json')
