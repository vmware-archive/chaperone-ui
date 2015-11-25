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
from __future__ import absolute_import

import fcntl
import logging
import os
import sys
import yaml

from django.conf import settings

LOG = logging.getLogger(__name__)

def include_constructor(loader, node):
    """Loads a yaml include file."""
    LOG.debug("Loading YAML(include) content from %s." % node.value)
    content = {}
    try:
        content = load(node.value)
    except IOError, err:
        LOG.debug("Cannot load YAML(include) content from %s because: %s." % (node.value, os.strerror(err.errno)))
    return content

def load(fname, inhibit_constructor=False):
    """Loads a yaml file, though with Chaperone extensions, like include files."""
    content = None
    try:
        yaml.add_constructor("!include", include_constructor)
        LOG.debug("Loading YAML content from %s." % fname)
        with open(fname, 'r') as fp:
            fcntl.flock(fp, fcntl.LOCK_SH)
            file_contents = fp.read()
            fcntl.flock(fp, fcntl.LOCK_UN)
        content = yaml.load(file_contents)
        LOG.debug(" ==> YAML content from %s.\n\t%s" % (fname, str(content)))
    except IOError, err:
        LOG.debug("Cannot load YAML content from %s because: %s." % (fname, os.strerror(err.errno)))

    if content == None:
        content = {}

    return content

def dump(fname, content):
    """ save object as yaml to a file."""
    LOG.debug("YAML dumping content: %s\n" % str(content))
    with open(fname, 'w+') as fp:
        fcntl.flock(fp, fcntl.LOCK_EX)
        fp.write(yaml.dump(content, default_flow_style=False))
        fcntl.flock(fp, fcntl.LOCK_UN)
        LOG.debug('YAML content file %s written' % fname)
