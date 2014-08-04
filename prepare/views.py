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

OPTIONAL_INPUT_TYPES = ('checkbox', 'file')


def _get_contents(filename):
    # Return data structure parsed from the given YAML file.
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        file_contents = fp.read()
        fcntl.flock(fp, fcntl.LOCK_UN)
    return yaml.load(file_contents)


def _get_sections(container_name, group_name):
    # Get group's sections, filling with saved values from the given file and
    # other information needed to display the group.
    base = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(base)

    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)
    hidden_fields = []

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
                    if gname != group_name:
                        continue
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

                                # Note if there's currently a version
                                # of the file saved.
                                if attr.get('input') == 'file':
                                    current_filename = '%s/%s' % (
                                        settings.PREPARE_FILES_DIR, attr_id)
                                    if os.path.exists(current_filename):
                                        attr['current'] = '1';

                                # Find fields that need to be hidden.
                                attr_show = attr.get('show')
                                if (attr_show and
                                        ((attr.get('input') in
                                          OPTIONAL_INPUT_TYPES and
                                          value != '1') or not value)):
                                    fields = [f.strip()
                                              for f in attr_show.split(',')]
                                    hidden_fields.extend(fields)

                    # Note which fields not to display.
                    for section in sections:
                        for _, attributes in section.iteritems():
                            for attr in attributes:
                                if attr['id'] in hidden_fields:
                                    attr['hide'] = '1'
                    return sections
    return None


def _get_attributes_by_id():
    # Return all attributes from the base file, keyed by attribute id.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(filename)
    attributes_by_id = {}
    # Which fields does the key depend on being set in order to be shown.
    show_deps = {}

    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for cname, groups in container.iteritems():
            # [{ ... }]
            for group in groups:
                # { 'Group': [...] }
                for gname, sections in group.iteritems():
                    # [{ ... }]
                    for section in sections:
                        # { 'Section': [...] }
                        for _, attributes in section.iteritems():
                            # [{ ... }]
                            for attr in attributes:
                                attr_id = attr['id']
                                attributes_by_id[attr_id] = attr

                                # Find dependencies.
                                attr_show = attr.get('show')
                                if attr_show:
                                    fields = [f.strip()
                                              for f in attr_show.split(',')]
                                    for fld in fields:
                                        current = show_deps.setdefault(fld, [])
                                        current.append(attr_id)
                                        show_deps[fld] = current

    # Add dependency information.
    for attr_id, fields in show_deps.iteritems():
        attributes_by_id[attr_id]['show_deps'] = fields
    return attributes_by_id


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

    attributes_by_id = _get_attributes_by_id()
    new_answers = request.REQUEST

    text = []
    for attr_id, data in attributes_by_id.iteritems():
        if new_answers and attr_id in new_answers:
            # Set new value.
            value = new_answers[attr_id]
            LOG.debug('Saving new value %s: %s' % (attr_id, value))

            # Check if there is a new file to save.
            if data.get('input') == 'file' and value == '1':
                src = request.FILES.get('file-%s' % attr_id)
                dst_filename = '%s/%s' % (settings.PREPARE_FILES_DIR, attr_id)
                if src:
                    with open(dst_filename, 'wb+') as dp:
                        for chunk in src.chunks():
                            dp.write(chunk)
                elif not os.path.exists(dst_filename):
                    # Should have a previously uploaded file available.
                    errors.append('File missing for %s.' % attr_id)
                    return errors
        elif saved_answers and attr_id in saved_answers:
            # Use currently saved value.
            value = saved_answers[attr_id]
            LOG.debug('Saving old value %s: %s' % (attr_id, value))
        else:
            # Use default value.
            value = data.get('default', '')
            LOG.debug('Saving default %s: %s' % (attr_id, value))

        # Escape backslashes and double quotation marks.
        value = value.replace('\\', '\\\\').replace('"', '\\"')
        text.append('%s: "%s"' % (attr_id, value or ''))

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
    sections = _get_sections(container_name, group_name)

    return render(request, 'prepare/_group.html', {
        'container_name': container_name,
        'group_name': group_name,
        'sections': sections,
    })


def _is_group_complete(sections, attributes_by_id=None):
    # Check if group has all required values set in its sections.
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    saved_answers = {}
    if os.path.exists(filename):
        # Get currently saved values.
        saved_answers = _get_contents(filename)

    # Caller might not have built the map if only one group is being checked
    # for completeness.
    if not attributes_by_id:
        attributes_by_id = _get_attributes_by_id()

    # [{ ... }]
    for section in sections:
        # { 'Section': [...] }
        for _, attributes in section.iteritems():
            # [{ ... }]
            for attr in attributes:
                attr_id = attr['id']

                if (not saved_answers.get(attr_id) and
                        not attr.get('input') in OPTIONAL_INPUT_TYPES):
                    show_deps = attributes_by_id[attr_id].get('show_deps')
                    if show_deps:
                        # Allowed to be empty only if all fields it's dependent
                        # upon are also empty.
                        for field in show_deps:
                            value = saved_answers.get(field)
                            input_type = attributes_by_id[field].get('input')
                            if ((input_type not in OPTIONAL_INPUT_TYPES and
                                    value) or value == '1'):
                                LOG.debug('%s missing whle %s set' %
                                          (attr_id, field))
                                return False
                        continue
                    else:
                        LOG.debug('%s missing' % attr_id)
                        return False
    return True


def get_group_status(request):
    """ Get current state of group, or all groups, if group name not given. """
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(filename)
    
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')
    data = {}
    attributes_by_id = _get_attributes_by_id()

    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for cname, groups in container.iteritems():
            if container_name and cname != container_name:
                continue

            data[cname] = {}
            # [{ ... }]
            for group in groups:
                # { 'Group': [...] }
                for gname, sections in group.iteritems():
                    if group_name and gname != group_name:
                        continue

                    is_complete = _is_group_complete(
                        sections, attributes_by_id=attributes_by_id)
                    data[cname][gname] = { 'complete': is_complete }
                    if group_name:
                        # Done - only one group requested.
                        return HttpResponse(json.dumps(data),
                                            content_type='application/json')
    # Return status for all groups.
    return HttpResponse(json.dumps(data), content_type='application/json')


def save_group(request):
    """ Save new answers for the group. """
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    errors = _write_answer_file(request, filename)
    # Get updated values, e.g., current versions of files.
    group = get_group(request).content 
    data = {
        'errors': errors,
        'group': group,
    }

    if not errors:
        container_name = request.REQUEST.get('cname')
        group_name = request.REQUEST.get('gname')
        sections = _get_sections(container_name, group_name)
        data['complete'] = _is_group_complete(sections)
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
