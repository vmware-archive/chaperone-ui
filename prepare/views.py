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

# Input types that are not required to have a value set.
OPTIONAL_INPUT_TYPES = ('checkbox', 'file')


def _get_contents(filename):
    # Return data structure parsed from the given YAML file.
    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        file_contents = fp.read()
        fcntl.flock(fp, fcntl.LOCK_UN)
    return yaml.load(file_contents)


def _has_value(attribute):
    # Return True if attribute has its value set.
    is_optional = attribute.get('input') in OPTIONAL_INPUT_TYPES
    value = attribute.get('value')
    if is_optional:
        return value == '1'
    else:
        return value


def _get_sections(container_name=None, group_name=None):
    # Return containers with all sections populated with the calculated
    # metadata for all attributes, or only the section for the given group in
    # the given container.
    base = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    containers = _get_contents(base)

    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)
    hidden_attributes = []

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

                                # Find attributes that need to be hidden.
                                attr_show = attr.get('show')
                                if attr_show and not _has_value(attr):
                                    ids = [f.strip()
                                           for f in attr_show.split(',')]
                                    hidden_attributes.extend(ids)

                    # Note which attributes not to display.
                    for section in sections:
                        for _, attributes in section.iteritems():
                            for attr in attributes:
                                if attr['id'] in hidden_attributes:
                                    attr['hide'] = '1'
                    if group_name:
                        return sections
    return containers


def _get_attributes_by_id(container_name=None, group_name=None):
    # Return all attribute metadata, keyed by attribute id, optionally for only
    # the given group in the given container.
    containers_or_sections = _get_sections(container_name=container_name,
                                           group_name=group_name)
    if group_name:
        # Already got sections for the group.
        all_sections = containers_or_sections
    else:
        all_sections = []
        # [{ ... }]
        for container in containers_or_sections:
            # { 'Container': { ... } }
            for _, groups in container.iteritems():
                # [{ ... }]
                for group in groups:
                    # { 'Group': [...] }
                    for _, sections in group.iteritems():
                        all_sections.extend(sections)

    attributes_by_id = {}
    # [{ ... }]
    for section in all_sections:
        # { 'Section': [...] }
        for _, attributes in section.iteritems():
            # [{ ... }]
            for attr in attributes:
                attr_id = attr['id']
                attributes_by_id[attr_id] = attr
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
    sections = _get_sections(container_name=container_name,
                             group_name=group_name)

    return render(request, 'prepare/_group.html', {
        'container_name': container_name,
        'group_name': group_name,
        'sections': sections,
    })


def _is_group_complete(sections):
    # Return True if group has all required values set in its sections.
    for section in sections:
        # { 'Section': [...] }
        for _, attributes in section.iteritems():
            # [{ ... }]
            for attr in attributes:
                if (not attr.get('input') in OPTIONAL_INPUT_TYPES and
                        not attr.get('optional') and not attr.get('hide') and
                        not _has_value(attr)):
                    LOG.debug('%s missing' % attr['id'])
                    return False
    return True


def get_group_status(request):
    """ Get current state of group, or all groups, if group name not given. """
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')
    containers_or_sections = _get_sections(container_name=container_name,
                                           group_name=group_name)
    data = {}

    if group_name:
        # Only dealing with one group.
        is_complete = _is_group_complete(containers_or_sections)
        data[container_name][group_name] = { 'complete': is_complete }
    else:
        # [{ ... }]
        for container in containers_or_sections:
            # { 'Container': { ... } }
            for cname, groups in container.iteritems():
                data[cname] = {}
                # [{ ... }]
                for group in groups:
                    # { 'Group': [...] }
                    for gname, sections in group.iteritems():
                        is_complete = _is_group_complete(sections)
                        data[cname][gname] = { 'complete': is_complete }
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
        sections = _get_sections(container_name=container_name,
                                 group_name=group_name)
        data['complete'] = _is_group_complete(sections)
    return HttpResponse(json.dumps(data), content_type='application/json')


def download_file(request, name):
    # Prevent directory traversal.
    basename = os.path.basename(name)
    filename = '%s/%s' % (settings.PREPARE_FILES_DIR, basename)

    # Loading file in chunks, in case it's large. Returning it as MIME type
    # text/plain causes Chrome to guess what file extension to add to the
    # filename during the download.
    response = HttpResponse(FileWrapper(open(filename)),
                            content_type='text/plain')
    response['Content-Length'] = os.path.getsize(filename)
    response['Content-Disposition'] = "attachment; filename=%s" % basename
    return response
