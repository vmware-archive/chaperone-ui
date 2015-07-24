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

from supervio.utils import getters

LOG = logging.getLogger(__name__)

# Global option cache
g_options_cache = {}

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
    #
    # See supervio/local_settings.py.example for schema.
    base = '%s/%s' % (settings.ANSWER_FILE_DIR, settings.ANSWER_FILE_BASE)
    menus = _get_contents(base)
    containers = []
    for menu in menus:
        for menu_name, menu_containers in menu.items():
            if menu_name == settings.PREPARE_MENU:
                containers = menu_containers
                break

    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    saved_answers = {}
    if os.path.exists(filename):
        saved_answers = _get_contents(filename)
    hidden_attributes = []
    shown_opt_attrs = []

    # Cache option values already retrieved in this request.
    g_options_cache = {}
    opt_filename = settings.INPUT_OPTIONS
    if os.path.exists(opt_filename):
        with open(opt_filename, 'r') as op:
            fcntl.flock(op, fcntl.LOCK_SH)
            g_options_cache = yaml.load(op)
            fcntl.flock(op, fcntl.LOCK_UN)

    # [{ ... }]
    for container in containers:
        # { 'Container': { ... } }
        for cname, groups in container.items():
            if container_name and cname != container_name:
                continue
            # [{ ... }]
            for group in groups:
                # { 'Group': [...] }
                for gname, sections in group.items():
                    if group_name and gname != group_name:
                        continue
                    # [{ ... }]
                    for section in sections:
                        # { 'Section': [...] }
                        for attributes in section.values():
                            # [{ ... }]
                            for attr in attributes:
				subsection = None
				input_type = attr.get('input')
				if input_type and input_type.lower() == 'multiform':
			            new_hidden_attributes, new_shown_opt_attrs, new_attributes = _get_multiform(attr,saved_answers)	
				    attributes.extend(new_attributes)
				else:
			            new_hidden_attributes, new_shown_opt_attrs, new_attr = _get_form(attr,saved_answers)	
				    attr=new_attr
				hidden_attributes.extend(new_hidden_attributes)
				shown_opt_attrs.extend(new_shown_opt_attrs)

                    # Note which attributes not to display.
                    for section in sections:
                        for attributes in section.values():
                            for attr in attributes:
                                attr_id = attr['id']
                                if (attr_id in hidden_attributes and
                                        attr_id not in shown_opt_attrs):
                                    attr['hide'] = '1'
                    if group_name:
                        return sections

    return containers

def _get_form( attr, saved_answers, attr_id=None):
  	hidden_attributes = []
  	shown_opt_attrs = []
	if not attr_id:
	    attr_id = attr['id']
	else:
	    attr['id'] = attr_id
  # Default name to id.
	if not attr.get('name'):
	    attr['name'] = attr_id

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

	attr_show = attr.get('show')
	if attr_show:
	    ids = [a.strip()
		   for a in attr_show.split(',')]
	    attr['show'] = ids
	    # Get attributes that need to be hidden.
	    if not _has_value(attr):
		hidden_attributes.extend(ids)

	attr_options = attr.get('options', [])
	if not isinstance(attr_options, list):
	    field_name = attr_options
	    # Make options a list now.
	    attr_options = []
	    if field_name in g_options_cache:
		opt_names = g_options_cache[field_name]
	    else:
		# Get options dynamically.
		fn_name = 'get_%s' % field_name
		fn = getattr(getters, fn_name)
		options = fn()
		if options:
		    opt_names = options.keys()
		    opt_names.sort()
		else:
		    opt_names = ['']
		g_options_cache[field_name] = opt_names

	    # Options for dropdown menu.
	    for name in opt_names:
		option = { 'id': name }
		attr_options.append(option)
	    attr['options'] = attr_options

	    # Use first option as default.
	    attr['default'] = (opt_names[0]
			       if opt_names else '')
	    if attr['value'] not in opt_names:
		attr['value'] = attr['default']

	if attr.get('input') == 'dropdown':
	    # Set default option.
	    default_option = { 'id': '' }
	    if not attr_options:
		attr['options'] = default_option
	    elif attr.get('optional'):
		attr_options.insert(0, default_option)

	# Populate options metadata.
	hidden_opt_attrs = []
	for option in attr_options:
	    option_id = option['id']
	    if not option.get('name'):
		option['name'] = option_id

	    option_show = option.get('show')
	    if option_show:
		attr['show'] = '1'
		ids = [o.strip()
		       for o in option_show.split(',')]
		option['show'] = ids
		hidden_opt_attrs.extend(ids)
		# Get attributes that need to be hidden.
		if attr.get('value') == option_id:
		    shown_opt_attrs.extend(ids)
		else:
		    hidden_attributes.extend(ids)
	# Need to know which fields to hide when
	# selected option changes.
	if hidden_opt_attrs:
	    for option in attr_options:
		ids = [o for o in hidden_opt_attrs if o
		       not in option.get('show', [])]
		option['hide'] = ids
	return hidden_attributes, shown_opt_attrs, attr

from copy import deepcopy
def _get_multiform(attr, answers):
  subsection = []
  hidden_attributes = []
  shown_opt_attrs = []
  for n in range(int(attr['min_items'])):
    items = deepcopy(attr['items'])
    for item in items:
      item_id = "%s_%d" % (item['id'], n)
      new_ha, new_soa, new_item = _get_form(item, answers, item_id)
      hidden_attributes.extend(new_ha)
      shown_opt_attrs.extend(new_soa)
      subsection.append(new_item)
  return hidden_attributes, shown_opt_attrs, subsection

def _get_attributes_by_id(container_name=None, group_name=None):
    # Return all attribute metadata, keyed by attribute id, optionally for only
    # the given group in the given container.
    #
    # See supervio/local_settings.py.example for schema.
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
            for groups in container.values():
                # [{ ... }]
                for group in groups:
                    # { 'Group': [...] }
                    for sections in group.values():
                        all_sections.extend(sections)

    attributes_by_id = {}
    # [{ ... }]
    for section in all_sections:
        # { 'Section': [...] }
        for attributes in section.values():
            # [{ ... }]
            for attr in attributes:
                attr_id = attr['id']
                attributes_by_id[attr_id] = attr
    return attributes_by_id


def write_answer_file(request, filename, new_answers=None):
    """Write out answer file, replacing old values with new ones, if given."""
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
    if not new_answers:
        new_answers = request.REQUEST

    answers_data = {}
    for attr_id, attr in attributes_by_id.items():
        if new_answers and attr_id in new_answers:
            # Set new value.
            value = new_answers[attr_id]
            LOG.debug('Saving new value %s: %s' % (attr_id, value))

            # Check if there is a new file to save.
            if attr.get('input') == 'file' and value == '1':
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
        else:
            # Use currently saved value.
            value = attr.get('value', '')
            LOG.debug('Saving old value %s: %s' % (attr_id, value))
        answers_data[attr_id] = str(value)

    with open(filename, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write(yaml.dump(answers_data, default_flow_style=False))
        fcntl.flock(fp, fcntl.LOCK_UN)
    LOG.info('File %s written' % filename)
    return errors


def get_group(request):
    """Display form to set answers for the sections in this group."""
    container_name = request.REQUEST.get('cname')
    group_name = request.REQUEST.get('gname')
    sections = _get_sections(container_name=container_name,
                             group_name=group_name)

    return render(request, 'prepare/_group.html', {
        'menu_name': settings.PREPARE_MENU,
        'container_name': container_name,
        'group_name': group_name,
        'sections': sections,
    })


def _is_group_complete(sections):
    # Return True if group has all required values set in its sections.
    for section in sections:
        # { 'Section': [...] }
        for attributes in section.values():
            # [{ ... }]
            for attr in attributes:
                if (not attr.get('input') in OPTIONAL_INPUT_TYPES and
                        not attr.get('optional') and not attr.get('hide') and
                        not _has_value(attr)):
                    LOG.debug('%s missing' % attr['id'])
                    return False
    return True


def get_group_status(request):
    """Get current state of group, or all groups, if group name not given."""
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
            for cname, groups in container.items():
                data[cname] = {}
                # [{ ... }]
                for group in groups:
                    # { 'Group': [...] }
                    for gname, sections in group.items():
                        is_complete = _is_group_complete(sections)
                        data[cname][gname] = { 'complete': is_complete }
    # Return status for all groups.
    return HttpResponse(json.dumps(data), content_type='application/json')


def save_group(request):
    """Save new answers for the group."""
    filename = '%s/%s' % (settings.ANSWER_FILE_DIR,
                          settings.ANSWER_FILE_DEFAULT)
    errors = write_answer_file(request, filename)
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
    """Retrieve file for user download."""
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
