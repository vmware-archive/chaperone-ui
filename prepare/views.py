import fcntl
import logging
import os
import yaml

from django.conf import settings
from django.shortcuts import render


LOG = logging.getLogger(__name__)


ANSWER_FILE_COOKIE = 'answerfile'
HEADING_TEMPLATE = """\
##############################
# %s
##############################"""
 

def _get_contents(filename):
    # Return data structure parsed from the given YAML file.
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        file_contents = fp.read()
        fcntl.flock(fp, fcntl.LOCK_UN)
    return yaml.load(file_contents)


def _get_base_answers(group_name=None):
    # Return dictionary of id/value pairs from the base file, optionally, for
    # only the group given.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        file_contents = fp.read()
        fcntl.flock(fp, fcntl.LOCK_UN)
        containers = yaml.load(file_contents)

    answers = {}
    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for _, groups in container.iteritems():
            # [{ ... }]
            for group in groups:
                # { 'Group': [...] }
                for gname, sections in group.iteritems():
                    # [{ ... }]
                    if group_name and gname != group_name:
                        continue
                    for section in sections:
                        # { 'Section': [...] }
                        for _, attributes in section.iteritems():
                            # [{ ... }]
                            for attr in attributes:
                                answers[attr['id']] = attr.get('default') or ''
    return answers


def _write_answer_file(filename, new_answers={}):
    # Write out answer file, replacing old values with new ones, if given.
    base_answers = _get_base_answers()
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)

    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)
        # Make a backup copy.
        backup_filename = '%s.bak' % filename
        with open(backup_filename, 'w+') as bp:
            fcntl.flock(bp, fcntl.LOCK_EX)
            bp.write(yaml.dump(saved_answers, default_flow_style=False))
            fcntl.flock(bp, fcntl.LOCK_UN)
            LOG.debug('Backup file %s written' % backup_filename)

    text = []
    for key, default in base_answers.iteritems():
        if new_answers and key in new_answers:
            # Set new value.
            value = new_answers[key]
            LOG.debug('Saving new value %s: %s' % (key, value))
        elif saved_answers and key in saved_answers:
            # Use currently saved value.
            value = saved_answers[key]
            LOG.debug('Saving old value %s: %s' % (key, value))
        else:
            # Use default value.
            value = default
            LOG.debug('Saving default %s: %s' % (key, value))
        text.append('%s: "%s"' % (key, value or ''))

    file_contents = '\n'.join(text)
    with open(filename, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write(file_contents)
        fcntl.flock(fp, fcntl.LOCK_UN)
    LOG.info('File %s written' % filename)


def get_group(request):
    """ Display form to set answers for the sections in this group. """
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')

    # Get group's sections, using saved values from the given file.
    base = "%s/%s" % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(base)
    filename = request.COOKIES.get(ANSWER_FILE_COOKIE)
    # TODO: Use user chosen file.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)

    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)
    group_sections = []

    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for cname, groups in container.iteritems():
            if cname == container_name:
                # [{ ... }]
                for group in groups:
                    # { 'Group': [...] }
                    for gname, sections in group.iteritems():
                        if gname == group_name:
                            # [{ ... }]
                            for section in sections:
                                # { 'Section': [...] }
                                for _, attributes in section.iteritems():
                                    # [{ ... }]
                                    for attr in attributes:
                                        attr_id = attr['id']
                                        if attr_id in saved_answers:
                                            # Used saved value if it exists.
                                            value = saved_answers[attr_id]
                                        else:
                                            value = attr.get('default')
                                        attr['value'] = value or ''
                    group_sections = sections
                    break  # out of "for gname, sections"

    return render(request, 'prepare/_group.html', {
        'container_name': container_name,
        'group_name': group_name,
        'sections': group_sections,
    })


def save_group(request):
    """ Save new answers for the group. """
    filename = request.COOKIES.get(ANSWER_FILE_COOKIE)
    # TODO: Use user chosen file.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    _write_answer_file(filename, request.REQUEST)
    return get_group(request)


def get_group_status(request):
    """ Check if there are any values missing from the group. """
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')
    base_answers = _get_base_answers(group_name=group_name)

    # Check for values in current file.
    filename = request.COOKIES.get(ANSWER_FILE_COOKIE)
    # TODO: Use user chosen file.
    filename = "%s/%s" % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)

    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)

    has_missing = False
    is_complete = False
    for key in base_answers.iterkeys():
        if not saved_answers.get(key):
            has_missing = True
            LOG.debug('Answer %s missing value' % key)
            break

    if not has_missing:
        LOG.debug('Group "%s" in container "%s" complete' %
                  (container_name, group_name))
        is_complete = True

    return render(request, 'prepare/_status.html', {
        'container_name': container_name,
        'group_name': group_name,
        'is_complete': is_complete,
    })
