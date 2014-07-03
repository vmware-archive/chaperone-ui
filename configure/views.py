import fcntl
import logging
import os
import subprocess
import time

from django.conf import settings
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render


LOG = logging.getLogger(__name__)


ACTION_RUN = 'run'
TMP_FILENAME = '%s.tmp'


def index(request, logname, configure_type):
    """ Show knobs to start running the configuration command. """
    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            file_contents = lp.read()

    return render(request, 'configure/_run.html', {
        'configure_type': configure_type,
        'log_contents': file_contents,
    })


def nsx_index(request):
    """ Display start page for NSX configuration command. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.NSX_CONFIGURE_LOG)
    return index(request, logname, 'nsx')


def sddc_index(request):
    """ Display start page for SDDC configuartion command. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.SDDC_CONFIGURE_LOG)
    return index(request, logname, 'sddc')


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


def _run_command(request, logname, command):
    # Run the given command, using any needed arguments from the request. The
    # command must be given as a list containing the command plus its
    # arguments.

    # Use temporary file to hold the most recent output, since the contents
    # were last consumed.
    tmp = TMP_FILENAME % logname
    if os.path.exists(logname):
        # Empty out log from previous run.
        with open(logname, 'w') as lp:
            lp.truncate(0)

    with open(tmp, 'w+') as tp:
        if request.REQUEST.get('debug'):
            command.append(settings.DEBUG_OPTION)
        LOG.info('Running "%s"' % ' '.join(command))
        proc = subprocess.Popen(command, stdout=tp, stderr=tp)


def run_nsx_command(request):
    """ Run configuration command for NSX. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.NSX_CONFIGURE_LOG)
    if request.REQUEST.get('action') == ACTION_RUN:
        command = settings.NSX_CONFIGURE_RUN
        message = 'Starting NSX configuration...\n'
    else:
        command = settings.NSX_CONFIGURE_VALIDATE
        message = 'Starting NSX configuration validation...\n'

    _run_command(request, logname, command)
    return HttpResponse(message, content_type='text/plain')


def run_sddc_command(request):
    """ Run configuration command for SDDC. """
    logname = '%s/%s' % (settings.VMOS_LOG_DIR, settings.SDDC_CONFIGURE_LOG)
    if request.REQUEST.get('action') == ACTION_RUN:
        command = settings.SDDC_CONFIGURE_RUN
        message = 'Starting SDDC configuration...\n'
    else:
        command = settings.SDDC_CONFIGURE_VALIDATE
        message = 'Starting SDDC configuration validation...\n'

    _run_command(request, logname, command)
    return HttpResponse(message, content_type='text/plain')
