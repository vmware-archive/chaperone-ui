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
import logging
import os
import subprocess
import time

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import slugify

from chaperone.utils import yaml

LOG = logging.getLogger(__name__)


def _get_logname(menu_name, group_name):
    return '%s/%s_%s.log' % (settings.CHAPERONE_LOG_DIR, slugify(menu_name),
                             slugify(group_name))


def _get_actions(menu_name, group_name):
    # Return action metadata for the given group. See
    # chaperone/local_settings.py.example for schema.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    menus = yaml.load(filename)

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

    LOG.debug('Preparing to run command from %s/%s/%s' % (menu_name, group_name, action_id))

    commands = []
    arguments = []
    for act in actions:
        act_id = act['id']
        LOG.debug('... checking act_id (%s) == action_id (%s)' % (act_id, action_id))
        if act_id == action_id:
            LOG.debug('... found act_id (%s) == action_id (%s)' % (act_id, action_id))
            commands = act.get('commands', [])
        arg = act.get('argument')
        if arg and request.REQUEST.get(act_id) == '1':
            LOG.debug('... appending arg: %s' % arg)
            arguments.append(arg)

    logname = _get_logname(menu_name, group_name)
    with open(logname, 'w+') as lp:
        num_cmds = len(commands)
        LOG.debug('... num_cmds = %d' % num_cmds)
        for i in range(0, num_cmds):
            cmd = commands[i]
            if arguments:
                cmd = '%s %s' % (cmd, ' '.join(arguments))

            LOG.debug('... cmd: %s' % cmd)

            # Set Python output to be unbuffered so any output is returned
            # immediately.
            env = os.environ
            env['PYTHONUNBUFFERED'] = '1'
            LOG.debug('Running "%s"' % cmd)
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
