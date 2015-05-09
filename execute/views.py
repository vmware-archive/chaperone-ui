import fcntl
import logging
import os
import subprocess
import time
import yaml

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import slugify


LOG = logging.getLogger(__name__)


def _get_logname(menu_name, group_name):
    return '%s/%s_%s.log' % (settings.SUPERVIO_LOG_DIR, slugify(menu_name),
                             slugify(group_name))


def _get_actions(menu_name, group_name):
    # Return action metadata for the given group. See
    # supervio/local_settings.py.example for schema.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        menus = yaml.load(fp)
        fcntl.flock(fp, fcntl.LOCK_UN)

    # [{ ... }]
    for menu in menus:
        # { 'Menu': { ... } }
        for mname, groups in menu.items():
            if mname != menu_name or mname == settings.PREPARE_MENU:
                continue
            # [{ ... }]
            for group in groups:
                # { 'Group' : { ... } }
                for gname, actions in group.items():
                    if gname == group_name:
                        return actions
    return []


def index(request):
    """Show knobs to start running the commands."""
    menu_name = request.REQUEST.get('mname')
    group_name = request.REQUEST.get('gname')
    actions = _get_actions(menu_name, group_name)

    logname = _get_logname(menu_name, group_name)
    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            fcntl.flock(lp, fcntl.LOCK_SH)
            file_contents = lp.read()
            fcntl.flock(lp, fcntl.LOCK_UN)

    return render(request, 'execute/_group.html', {
        'menu_name': menu_name,
        'group_name': group_name,
        'actions': actions,
        'log_contents': file_contents,
    })


def run_commands(request):
    """Run the commands for the given action."""
    menu_name = request.REQUEST.get('mname')
    group_name = request.REQUEST.get('gname')
    action_id = request.REQUEST.get('aid')
    actions = _get_actions(menu_name, group_name)

    commands = []
    arguments = []
    for act in actions:
        act_id = act['id']
        if act_id == action_id:
            commands = act.get('commands', [])
        arg = act.get('argument')
        if arg and request.REQUEST.get(act_id) == '1':
            arguments.append(arg)

    logname = _get_logname(menu_name, group_name)
    with open(logname, 'w+') as lp:
        num_cmds = len(commands)
        for i in range(0, num_cmds):
            cmd = commands[i]
            if arguments:
                cmd = '%s %s' % (cmd, ' '.join(arguments))

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
    # AJAX polling will check for output.
    return HttpResponse('')


def tail_log(request):
    """Return output written to the log file for this group since the last
    call made to this.
    """
    menu_name = request.REQUEST.get('mname')
    group_name = request.REQUEST.get('gname')
    logname = _get_logname(menu_name, group_name)

    file_contents = ''
    if os.path.exists(logname):
        with open(logname, 'r') as lp:
            # Read what has been written to the file so far.
            fcntl.flock(lp, fcntl.LOCK_SH)
            file_contents = lp.read()
            fcntl.flock(lp, fcntl.LOCK_UN)
    return HttpResponse(file_contents, content_type='text/plain')
