import fcntl
import json
import logging
import os
import re
import subprocess
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render


LOG = logging.getLogger(__name__)

ACTION_RUN = 'run'


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
