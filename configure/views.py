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
HV_TEMPLATE = """%s ansible_ssh_user="%s" ansible_ssh_pass="%s" nic="[%s]" bond_mode="%s" transport_ip="%s" transport_mask="%s" transport_gateway="%s"
"""
HV_COUNT_COOKIE = 'hvcount'
TMP_FILENAME = '%s.tmp'


def _index(request, logname, configure_type):
    # Show knobs to start running the configuration commands.
    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            file_contents = lp.read()

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
    # Show knobs to start running the configuration commands.
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.HVS_CONFIGURE_LOG)
    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            file_contents = lp.read()

    response = render(request, 'configure/_hvs.html', {
        'log_contents': file_contents,
        'count': '1',
    });
    # Initialize cookie value.
    response.set_cookie(HV_COUNT_COOKIE, '1')
    return response


def _run_commands(request, logname, commands):
    # Run the given commands, using any needed options from the request. The
    # commands must be given as a list, one string per command plus its
    # arguments and options.

    # Use temporary file to hold the most recent output, since the contents
    # were last consumed.
    tmp = TMP_FILENAME % logname
    if os.path.exists(logname):
        # Empty out log from previous run.
        with open(logname, 'w') as lp:
            lp.truncate(0)

    with open(tmp, 'w+') as tp:
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
            proc = subprocess.Popen(cmd.split(), stdout=tp, stderr=tp, env=env)
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
        hv[arg] = value

    # Write out all the input values into the init file.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.HVS_FILE)
    with open(filename, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write('[hypervisors]\n')
        for hv in hvs.values():
            nics = ["'%s'" % n for n in hv.get('nic', '').split(',')]
            fp.write(HV_TEMPLATE % (hv.get('host', ''), hv.get('user', ''),
                                    hv.get('password', ''), ', '.join(nics),
                                    hv.get('bond', ''), hv.get('txip', ''),
                                    hv.get('txmask', ''), hv.get('txgw', '')))
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
    tmp = TMP_FILENAME % logname
    file_contents = ''
    
    if os.path.exists(tmp):
        with open(tmp, 'r+') as tp:
            # Read what has been written to the file so far.
            fcntl.flock(tp, fcntl.LOCK_EX)
            file_contents = tp.read()
            # Empty out what we've read.
            tp.truncate(0)
            fcntl.flock(tp, fcntl.LOCK_UN)

    if file_contents:
        # After tmp file gets truncated, subprocess is still writing the output
        # to the last file position, so the truncated part gets filled with
        # nul bytes. Remove those.
        file_contents = file_contents.lstrip('\x00')
        with open(logname, 'a+') as lp:
            # Now write the contents back out to the complete log file.
            fcntl.flock(lp, fcntl.LOCK_EX)
            lp.write(file_contents)
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

    try:
        command = 'ansible-playbook -i %s/nics.ini %s/%s' % (
            settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_DIR,
            settings.NICS_FILE)
        LOG.info('Running "%s"' % command)
        output = subprocess.check_output(command.split())
    except subprocess.CalledProcessError as e:
        return HttpResponse('')

    # Parse out NIC names from output.
    nics = set(re.findall(r'(vmnic[0-9]+)', output))
    nics_json = json.dumps(list(nics))
    return HttpResponse(nics_json, content_type='application/json')
