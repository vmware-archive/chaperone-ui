import fcntl
import json
import logging
import mimetypes
import os
import yaml

from django.conf import settings
from django.core.servers.basehttp import FileWrapper
from django.http import HttpResponse
from django.shortcuts import render


LOG = logging.getLogger(__name__)


ANSWER_FILE_COOKIE = 'answerfile'
 

def _get_contents(filename):
    # Return data structure parsed from the given YAML file.
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        file_contents = fp.read()
        fcntl.flock(fp, fcntl.LOCK_UN)
    return yaml.load(file_contents)


def _get_sections(container_name, group_name):
    # Return sections for the given group in the given container.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(filename)

    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for cname, groups in container.iteritems():
            if cname != container_name:
                continue
            # [{ ... }]
            for group in groups:
                # { 'Group': [...] }
                for gname, sections in group.iteritems():
                    if gname == group_name:
                        return sections
    return None


def _get_input_types(container_name, group_name):
    # Return input types for the attributes in the given group in the given
    # container.
    sections = _get_sections(container_name, group_name)
    input_types = {}
    # [{ ... }]
    for section in sections:
        # { 'Section': [...] }
        for _, attributes in section.iteritems():
            # [{ ... }]
            for attr in attributes:
                input_types[attr['id']] = attr.get('input')
    return input_types


def _get_answer_default(attribute):
    # Return default value for the given attribute. Default to empty string.
    return attribute.get('default') or ''


def _get_base_answers(container_name=None, group_name=None):
    # Return dictionary of id/value pairs from the base file, optionally, for
    # only the given group in the given container.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(filename)

    answers = {}
    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for cname, groups in container.iteritems():
            if container_name and cname != container_name:
                continue
            # [{ ... }]
            for group in groups:
                # { 'Group': [...] }
                for gname, sections in group.iteritems():
                    if group_name and gname != group_name:
                        continue
                    # [{ ... }]
                    for section in sections:
                        # { 'Section': [...] }
                        for _, attributes in section.iteritems():
                            # [{ ... }]
                            for attr in attributes:
                                answers[attr['id']] = _get_answer_default(attr)
    return answers


def _write_answer_file(request, filename):
    # Write out answer file, replacing old values with new ones, if given.
    errors = []
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
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

    base_answers = _get_base_answers()
    new_answers = request.REQUEST
    container_name = new_answers.get('cname')
    group_name = new_answers.get('gname')
    input_types = _get_input_types(container_name, group_name)

    text = []
    for key, default in base_answers.iteritems():
        if new_answers and key in new_answers:
            # Set new value.
            value = new_answers[key]
            LOG.debug('Saving new value %s: %s' % (key, value))

            # Check if there is a new file to save.
            if input_types.get(key) == 'file' and value == '1':
                src = request.FILES.get('file-%s' % key)
                dst_filename = '%s/%s' % (settings.PREPARE_FILES_DIR, key)
                if src:
                    with open(dst_filename, 'wb+') as dp:
                        for chunk in src.chunks():
                            dp.write(chunk)
                elif not os.path.exists(dst_filename):
                    # Should have a previously uploaded file available.
                    errors.append('File missing for %s.' % key)
                    return errors
                                
        elif saved_answers and key in saved_answers:
            # Use currently saved value.
            value = saved_answers[key]
            LOG.debug('Saving old value %s: %s' % (key, value))
        else:
            # Use default value.
            value = default
            LOG.debug('Saving default %s: %s' % (key, value))
        # Escape backslashes and double quotation marks.
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        text.append('%s: "%s"' % (key, value or ''))

    file_contents = '\n'.join(text)
    with open(filename, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write(file_contents)
        fcntl.flock(fp, fcntl.LOCK_UN)
    LOG.info('File %s written' % filename)
    return errors


def get_group(request):
    """ Display form to set answers for the sections in this group. """
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')

    # Get group's sections, using saved values from the given file.
    base = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(base)
    filename = request.COOKIES.get(ANSWER_FILE_COOKIE)
    # TODO: Use user chosen file.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
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
                                            value = _get_answer_default(attr)
                                        attr['value'] = value or ''
                                        if attr.get('input') == 'file':
                                            filename = '%s/%s' % (
                                                settings.PREPARE_FILES_DIR,
                                                attr_id)
                                            if os.path.exists(filename):
                                                attr['current'] = '1';
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
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    errors = _write_answer_file(request, filename)
    # Get current state of attributes, e.g., current versions of files.
    group = get_group(request).content 
    data = { 'errors': errors, 'group': group }
    return HttpResponse(json.dumps(data), content_type='application/json')


def get_group_status(request):
    """ Check if there are any values missing from the group. """
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')
    base_answers = _get_base_answers(container_name=container_name,
                                     group_name=group_name)

    # Check for values in current file.
    filename = request.COOKIES.get(ANSWER_FILE_COOKIE)
    # TODO: Use user chosen file.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)
    input_types = {}

    has_missing = False
    is_complete = False
    for key in base_answers.iterkeys():
        if not saved_answers.get(key):
            # Lazy initialization.
            if not input_types:
                input_types = _get_input_types(container_name, group_name)
            # Ignore checkboxes, because setting it is not required.
            if not input_types.get(key) in ('checkbox', 'file'):
                has_missing = True
                LOG.debug('Answer %s missing value' % key)
                break

    if not has_missing:
        LOG.debug('Group "%s" in container "%s" complete' %
                  (container_name, group_name))
        is_complete = True

    data = { 'complete': is_complete }
    return HttpResponse(json.dumps(data), content_type='application/json')


def download_file(request, name):
    # Prevent directory traversal.
    basename = os.path.basename(name)
    filename = '%s/%s' % (settings.PREPARE_FILES_DIR, basename)

    # Loading file in chunks, in case it's large.
    response = HttpResponse(FileWrapper(open(filename)),
                            content_type=mimetypes.guess_type(filename)[0])
    response['Content-Length'] = os.path.getsize(filename)
    response['Content-Disposition'] = "attachment; filename=%s" % basename
    return response
