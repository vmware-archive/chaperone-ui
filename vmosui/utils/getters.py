# get_foos() returns either a dict of the foo objects keyed by name, for
# dropdown fields, or the value saved for foo, for text fields. Used to
# populate options for fields with attribute "options: foos".
import fcntl
import inspect
import logging
import os
import sys
import yaml

from django.conf import settings

from pyVmomi import vim
from pyVim import connect


LOG = logging.getLogger(__name__)

COMP_VC_CLUSTER = 'comp_vc_cluster'
COMP_VC_DATACENTER = 'comp_vc_datacenter'
COMP_VC_PASSWORD = 'comp_vc_password'
COMP_VC_USERNAME = 'comp_vc_username'
COMP_VC = 'comp_vc'

MGMT_VC_CLUSTER = 'mgmt_vc_cluster'
MGMT_VC_DATACENTER = 'mgmt_vc_datacenter'
MGMT_VC_PASSWORD = 'mgmt_vc_password'
MGMT_VC_USERNAME = 'mgmt_vc_username'
MGMT_VC = 'mgmt_vc'

VCENTER_PORT = 443


def _get_vcenter_data():
    filename = settings.VCENTER_SETTINGS
    if not os.path.exists(filename):
        LOG.info('No file %s' % filename)
        return {}

    with open(filename, 'r') as fp:
        fcntl.flock(fp, fcntl.LOCK_SH)
        file_contents = fp.read()
        fcntl.flock(fp, fcntl.LOCK_UN)
    return yaml.load(file_contents)


def vcenter_connection(vcenter, username, password):
    """Returns a vCenter service instance, connected with the given login
    information.
    """
    if not all([vcenter, username, password]):
        LOG.error('vCenter host, username, and password required')
        return None
    try:
        service_instance = connect.SmartConnect(host=vcenter, user=username,
                                                pwd=password,
                                                port=VCENTER_PORT)
    except vim.fault.InvalidLogin as e:
        LOG.error('Could not connect to %s: %s' % (vcenter, e.msg))
        return None
    return service_instance


def get_comp_vc():
    """Returns saved name or IP address of compute vCenter host."""
    vcenter_data = _get_vcenter_data()
    return vcenter_data.get(COMP_VC)


def get_mgmt_vc():
    """Returns saved name or IP address of management vCenter host."""
    vcenter_data = _get_vcenter_data()
    return vcenter_data.get(MGMT_VC)


def get_comp_vc_username():
    """Returns saved login username for compute vCenter."""
    vcenter_data = _get_vcenter_data()
    return vcenter_data.get(COMP_VC_USERNAME)


def get_mgmt_vc_username():
    """Returns saved login username for management vCenter."""
    vcenter_data = _get_vcenter_data()
    return vcenter_data.get(MGMT_VC_USERNAME)


def get_comp_vc_password():
    """Returns saved login password for compute vCenter."""
    vcenter_data = _get_vcenter_data()
    return vcenter_data.get(COMP_VC_PASSWORD)


def get_mgmt_vc_password():
    """Returns saved login password for management vCenter."""
    vcenter_data = _get_vcenter_data()
    return vcenter_data.get(MGMT_VC_PASSWORD)


def _get_datacenters(vcenter_field, username_field, password_field,
                     datacenter_field, vcenter, username, password,
                     datacenter=None):
    LOG.debug('_get_datacenters: %s, %s, %s, %s' % (vcenter, username,
                                                    password, datacenter))
    vcenter_data = _get_vcenter_data()
    if vcenter is None:
        vcenter = vcenter_data.get(vcenter_field)
    if username is None:
        username = vcenter_data.get(username_field)
    if password is None:
        password = vcenter_data.get(password_field)
    if datacenter is None:
        datacenter = vcenter_data.get(datacenter_field)

    service_instance = vcenter_connection(vcenter, username, password)
    if not service_instance:
        return None
    content = service_instance.RetrieveContent()
    dcview = content.viewManager.CreateContainerView(content.rootFolder,
                                                     [vim.Datacenter], True)
    datacenters = dcview.view
    dcview.Destroy()
    connect.Disconnect

    datacenters_by_name = {}
    for dc in datacenters:
        if datacenter and dc.name != datacenter:
            continue
        datacenters_by_name[dc.name] = dc
    return datacenters_by_name


def get_comp_vc_datacenters(vcenter=None, username=None, password=None,
                            datacenter=None):
    """Returns a dict of datacenters in the compute vCenter, keyed by name,
    optionally limited to only the given datacenter. Pass in empty string for
    'datacenter' to get all datacenters.
    """
    LOG.debug('get_comp_vc_datacenters caller: %s', inspect.stack()[1][3])
    return _get_datacenters(COMP_VC, COMP_VC_USERNAME, COMP_VC_PASSWORD,
                            COMP_VC_DATACENTER, vcenter, username, password,
                            datacenter=datacenter)


def get_mgmt_vc_datacenters(vcenter=None, username=None, password=None,
                            datacenter=None):
    """Returns a dict of datacenters in the management vCenter, keyed by
    name, optionally limited to only the given datacenter. Pass in empty string
    for 'datacenter' to get all datacenters.
    """
    LOG.debug('get_mgmt_vc_datacenters caller: %s', inspect.stack()[1][3])
    return _get_datacenters(MGMT_VC, MGMT_VC_USERNAME, MGMT_VC_PASSWORD,
                            MGMT_VC_DATACENTER, vcenter, username, password,
                            datacenter=datacenter)


def _get_clusters(vcenter_field, username_field, password_field,
                  datacenter_field, cluster_field, vcenter, username, password,
                  datacenter=None, cluster=None):
    LOG.debug('_get_clusters: %s, %s, %s, %s' % (vcenter, username,
                                                 password, datacenter))
    vcenter_data = _get_vcenter_data()
    if vcenter is None:
        vcenter = vcenter_data.get(vcenter_field)
    if username is None:
        username = vcenter_data.get(username_field)
    if password is None:
        password = vcenter_data.get(password_field)
    if datacenter is None:
        datacenter = vcenter_data.get(datacenter_field)
    if cluster is None:
        cluster = vcenter_data.get(cluster_field)

    service_instance = vcenter_connection(vcenter, username, password)
    if not service_instance:
        return None
    content = service_instance.RetrieveContent()
    connect.Disconnect

    datacenters = _get_datacenters(vcenter_field, username_field,
                                   password_field, datacenter_field, vcenter,
                                   username, password, datacenter=datacenter)
    clusters_by_name = {}
    for dc_name, dc in datacenters.iteritems():
        if datacenter and dc_name != datacenter: 
            continue
        clusterview = content.viewManager.CreateContainerView(
            dc, [vim.ClusterComputeResource], True)
        clusters = clusterview.view
        clusterview.Destroy() 

        for cl in clusters:
            if cluster and cl.name != cluster:
                continue
            clusters_by_name[cl.name] = cl
    return clusters_by_name


def get_comp_vc_clusters(vcenter=None, username=None, password=None,
                         datacenter=None, cluster=None):
    """Returns a dict of clusters in the compute vCenter, optionally only from
    the given datacenter and limited to only the given cluster. Pass in empty
    string for 'datacenter'/'cluster' to get all datcenters/clusters.
    """
    LOG.debug('get_comp_vc_clusters caller: %s', inspect.stack()[1][3])
    return _get_clusters(COMP_VC, COMP_VC_USERNAME, COMP_VC_PASSWORD,
                         COMP_VC_DATACENTER, COMP_VC_CLUSTER, vcenter,
                         username, password, datacenter=datacenter,
                         cluster=cluster)


def get_mgmt_vc_clusters(vcenter=None, username=None, password=None,
                         datacenter=None, cluster=None):
    """Returns a dict of clusters in the management vCenter, optionally only
    from the given datacenter and limited to only the given cluster. Pass in
    empty string for 'datacenter'/'cluster' to get all datcenters/clusters.
    """
    LOG.debug('get_mgmt_vc_clusters caller: %s', inspect.stack()[1][3])
    return _get_clusters(MGMT_VC, MGMT_VC_USERNAME, MGMT_VC_PASSWORD,
                         MGMT_VC_DATACENTER, MGMT_VC_CLUSTER, vcenter,
                         username, password, datacenter=datacenter,
                         cluster=cluster)


def _get_hosts(vcenter_field, username_field, password_field, datacenter_field,
               cluster_field):
    vcenter_data = _get_vcenter_data()
    vcenter = vcenter_data.get(vcenter_field)
    username = vcenter_data.get(username_field)
    password = vcenter_data.get(password_field)
    datacenter = vcenter_data.get(datacenter_field)
    cluster = vcenter_data.get(cluster_field)

    service_instance = vcenter_connection(vcenter, username, password)
    if not service_instance:
        return None
    content = service_instance.RetrieveContent()
    connect.Disconnect

    clusters = _get_clusters(vcenter_field, username_field, password_field,
                             datacenter_field, cluster_field, vcenter,
                             username, password, datacenter=datacenter,
                             cluster=cluster)
    hosts_by_name = {}
    for cl_name, cl in clusters.iteritems():
        if cluster and cl_name != cluster:
            continue
        hostsview = content.viewManager.CreateContainerView(
            cl, [vim.HostSystem], True)
        hosts = hostsview.view
        hostsview.Destroy()

        for host in hosts:
            hosts_by_name[host.name] = host
    return hosts_by_name


def get_comp_vc_hosts():
    """Returns a dict of hosts in the saved compute vCenter cluster."""
    return _get_hosts(COMP_VC, COMP_VC_USERNAME, COMP_VC_PASSWORD,
                      COMP_VC_DATACENTER, COMP_VC_CLUSTER)


def get_mgmt_vc_hosts():
    """Returns a dict of hosts in the saved management vCenter cluster."""
    return _get_hosts(MGMT_VC, MGMT_VC_USERNAME, MGMT_VC_PASSWORD,
                      MGMT_VC_DATACENTER, MGMT_VC_CLUSTER)


def _get_datastores(vcenter_field, username_field, password_field,
                    datacenter_field, cluster_field):
    hosts = _get_hosts(vcenter_field, username_field, password_field,
                       datacenter_field, cluster_field)
    if not hosts:
        return None
    # Include empty value, to make user explicitly choose option.
    datastores_by_name = { '': None }

    for host in hosts.values():
        for datastore in host.datastore:
            datastores_by_name[datastore.name] = datastore
    return datastores_by_name 


def get_comp_vc_datastores():
    """Returns a dict of datastores in the saved compute vCenter cluster."""
    LOG.debug('get_comp_vc_datastores caller: %s', inspect.stack()[1][3])
    return _get_datastores(COMP_VC, COMP_VC_USERNAME, COMP_VC_PASSWORD,
                           COMP_VC_DATACENTER, COMP_VC_CLUSTER)


def get_mgmt_vc_datastores():
    """Returns a dict of datastores in the saved management vCenter."""
    LOG.debug('get_mgmt_vc_datastores caller: %s', inspect.stack()[1][3])
    return _get_datastores(MGMT_VC, MGMT_VC_USERNAME, MGMT_VC_PASSWORD,
                           MGMT_VC_DATACENTER, MGMT_VC_CLUSTER)


def _get_networks(vcenter_field, username_field, password_field,
                  datacenter_field, cluster_field):
    hosts = _get_hosts(vcenter_field, username_field, password_field,
                       datacenter_field, cluster_field)
    if not hosts:
        return None
    # Include empty value, to make user explicitly choose option.
    networks_by_name = { '': None }

    for host in hosts.values():
        for network in host.network:
            networks_by_name[network.name] = network
    return networks_by_name


def get_comp_vc_networks():
    """Returns a dict of networks in the saved compute vCenter cluster."""
    LOG.debug('get_comp_vc_networks caller: %s', inspect.stack()[1][3])
    return _get_networks(COMP_VC, COMP_VC_USERNAME, COMP_VC_PASSWORD,
                         COMP_VC_DATACENTER, COMP_VC_CLUSTER)


def get_mgmt_vc_networks():
    """Returns a dict of networks in the saved management vCenter cluster."""
    LOG.debug('get_mgmt_vc_networks caller: %s', inspect.stack()[1][3])
    return _get_networks(MGMT_VC, MGMT_VC_USERNAME, MGMT_VC_PASSWORD,
                         MGMT_VC_DATACENTER, MGMT_VC_CLUSTER)
