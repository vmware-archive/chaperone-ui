import fcntl
import os
import yaml

from django import forms
from django.conf import settings

from vmosui.utils import getters


class DynamicChoiceField(forms.ChoiceField): 
    # Avoid error about choice not being valid when field's options are
    # dynamically populated.
    def clean(self, value): 
        return value


def _initialize_values(form_fields, vcenter_data, vcenter_field,
                       username_field, password_field, datacenter_field,
                       cluster_field):
    vcenter = vcenter_data.get(vcenter_field, '')
    form_fields[vcenter_field].initial = vcenter

    username = vcenter_data.get(username_field, '')
    form_fields[username_field].initial = username

    password = vcenter_data.get(password_field, '')
    form_fields[password_field].initial = password
    # Need this to make value appear in text box.
    form_fields[password_field].widget.render_value = True

    datacenter = vcenter_data.get(datacenter_field, '')
    form_fields[datacenter_field].initial = datacenter

    cluster = vcenter_data.get(cluster_field, '')
    form_fields[cluster_field].initial = cluster

    if all([vcenter, username, password]):
        # Get datacenters in the vCenter.
        fn_name = 'get_%s' % datacenter_field
        fn = getattr(getters, fn_name)
        # Pass in blank datacenter to get all options.
        datacenters = fn(vcenter=vcenter, username=username, password=password,
                         datacenter='')
        datacenter_choices = [('', '-- select --')]
        if datacenters is not None:
            opt_names = datacenters.keys()
            opt_names.sort()
            for name in opt_names:
                datacenter_choices.append((name, name))
        form_fields[datacenter_field].choices = datacenter_choices

        if datacenter and datacenters:
            # Get clusters in this vCenter's datacenter.
            fn_name = 'get_%s' % cluster_field
            fn = getattr(getters, fn_name)
            # Pass in blank cluster to get all options.
            clusters = fn(vcenter=vcenter, username=username,
                          password=password, datacenter=datacenter, cluster='')
            cluster_choices = [('', '-- select --')]
            if clusters is not None:
                opt_names = clusters.keys()
                opt_names.sort()
                for name in opt_names:
                    cluster_choices.append((name, name))
            form_fields[cluster_field].choices = cluster_choices


class VCenterForm(forms.Form):
    """ Form to enter vCenter settings. """
    mgmt_vc = forms.CharField(label='Management vCenter', max_length=254)
    mgmt_vc_username = forms.CharField(label='Management vCenter User',
                                       max_length=254)
    mgmt_vc_password = forms.CharField(label='Management vCenter Password',
                                    max_length=254, widget=forms.PasswordInput)
    mgmt_vc_datacenter = DynamicChoiceField(
        label='Management vCenter Datacenter')
    mgmt_vc_cluster = DynamicChoiceField(label='Management vCenter Cluster')

    comp_vc = forms.CharField(label='Compute vCenter', max_length=254)
    comp_vc_username = forms.CharField(label='Compute vCenter User',
                                       max_length=254)
    comp_vc_password = forms.CharField(label='Compute vCenter Password',
                                       max_length=254,
                                       widget=forms.PasswordInput)
    comp_vc_datacenter = DynamicChoiceField(label='Compute vCenter Datacenter')
    comp_vc_cluster = DynamicChoiceField(label='Compute vCenter Cluster')

    def __init__(self, *args, **kwargs):
        super(VCenterForm, self).__init__(*args, **kwargs)
        for field in self.fields.itervalues():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['required'] = 'required'

        # Note which fields contain login information.
        login_fields = [getters.COMP_VC, getters.COMP_VC_USERNAME,
                        getters.COMP_VC_PASSWORD, getters.MGMT_VC,
                        getters.MGMT_VC_USERNAME, getters.MGMT_VC_PASSWORD]
        for fieldname in login_fields:
            self.fields[fieldname].widget.attrs['class'] += ' vc-login'

        # Note which fields are populated based on the values in these.
        self.fields[getters.COMP_VC_DATACENTER].widget.attrs['data-target'] = \
            getters.COMP_VC_CLUSTER
        self.fields[getters.MGMT_VC_DATACENTER].widget.attrs['data-target'] = \
            getters.MGMT_VC_CLUSTER

        # Get currently saved vCenter settings.
        filename = settings.VCENTER_SETTINGS
        if not os.path.exists(filename):
            return

        with open(filename, 'r') as fp:
            fcntl.flock(fp, fcntl.LOCK_SH)
            file_contents = fp.read()
            fcntl.flock(fp, fcntl.LOCK_UN)
        vcenter_data = yaml.load(file_contents)

        _initialize_values(self.fields, vcenter_data, getters.COMP_VC,
                           getters.COMP_VC_USERNAME, getters.COMP_VC_PASSWORD,
                           getters.COMP_VC_DATACENTER, getters.COMP_VC_CLUSTER)
        _initialize_values(self.fields, vcenter_data, getters.MGMT_VC,
                           getters.MGMT_VC_USERNAME, getters.MGMT_VC_PASSWORD,
                           getters.MGMT_VC_DATACENTER, getters.MGMT_VC_CLUSTER)
