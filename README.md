# chaperone-ui

This is the Chaperone user interface ("UI") project. This repository provides
for the Django based Chaperone UI. It is based on the code originally targeted
at a project known as VSOM, but has been adapted for use in Chaperone.

## Getting Started
If you intend to use this code outside the context of Chaperone, you
can read the setup.py and local_setup.py files useful information.

## The Right Way
A much easier way to wprk with this code is via the Chaperone Ansible
Playbooks project (and related modules and roles). That is
within the ansible-playbooks-chaperone project, which has a complete
README.md file for setting up Chaperone for both use and development.

## Some YAML Additions
As the Chaperone Django application utilizes YAML files to form the UI
itself, an include capability for YAML was deemed useful. Therefore we
created that facility. In any UI (e.g., base.yml) definition file, a
value of a node can be of the form:

    !include /full/path/to/some/file.yml

and the path given will be read as a YAML insert. For example:

---
```yaml
- Prepare:
  - "Users and Groups":
    - "Service Accounts":
      - "AD Service Account": !include /var/lib/chaperone/adsa.yml
. . .
```

For more information on how to structure the Prepare and Install
menus, see the [Chaperone templates](https://github.com/vmware/ansible-role-chaperone/tree/master/templates/var/lib/chaperone)
and also the code that documents the structure [within this project](chaperone/local_settings.py.example).

# License and Copyright
 
Copyright 2015 VMware, Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

