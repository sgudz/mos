import os
import json
import logging
import uuid
import urllib2
import time
import netaddr

from nailgun_client import NailgunClient

logger = logging.getLogger(__name__)


class FuelManager(object):
    def __init__(self, cluster_settings, fuel_ip, lab_name):
        self.cluster_settings = cluster_settings
        self.fuel_ip = fuel_ip
        self.lab_name = lab_name

    def delete_environment(self):
        # Clean Fuel cluster
        client = NailgunClient(self.fuel_ip)
        for cluster in client.list_clusters():
            client.delete_cluster(cluster['id'])
            while True:
                try:
                    client.get_cluster(cluster['id'])
                except urllib2.HTTPError as e:
                    if str(e) == "HTTP Error 404: Not Found":
                        break
                    else:
                        raise
                except Exception:
                    raise
                time.sleep(1)

    def create_environment(self):
        logger.debug('Create fuel environment')
        client = NailgunClient(self.fuel_ip)
        release_id = client.get_release_id(
            self.cluster_settings['release_name'])

        data = {"name": self.cluster_settings['env_name'],
                "release": release_id,
                "mode": self.cluster_settings['config_mode'],
                "net_provider": self.cluster_settings['net_provider']}
        if self.cluster_settings.get('net_segment_type'):
            data['net_segment_type'] = \
                self.cluster_settings['net_segment_type']

        client.create_cluster(data)

        if self.cluster_settings.get("lma") == "true":
            lma = True
        else:
            lma = False

        cluster_id = client.get_cluster_id(self.cluster_settings['env_name'])
        attributes = client.get_cluster_attributes(cluster_id)

        settings = self.generate_components_config()

        for option in settings:
            section = False
            if option in ('sahara', 'murano', 'ceilometer'):
                section = 'additional_components'
            if option in ('volumes_ceph', 'images_ceph', 'ephemeral_ceph',
                          'objects_ceph', 'osd_pool_size', 'volumes_lvm'):
                section = 'storage'
            if section:
                attributes['editable'][section][option]['value'] = settings[
                    option]

        hpv_data = attributes['editable']['common']['libvirt_type']
        hpv_data['value'] = str(self.cluster_settings['virt_type'])

        debug = self.cluster_settings.get('debug', 'false')
        auto_assign = self.cluster_settings.get('auto_assign_floating_ip',
                                                'false')
        nova_quota = self.cluster_settings.get('nova_quota', 'true')

        attributes['editable']['common']['debug']['value'] = json.loads(debug)
        attributes['editable']['common'][
            'auto_assign_floating_ip']['value'] = json.loads(auto_assign)
        attributes['editable']['common']['nova_quota']['value'] = \
            json.loads(nova_quota)

        attributes['editable']['provision']['method']['value'] = \
            self.cluster_settings.get('provision_method', 'cobbler')

        for repo_item in \
                attributes['editable']['repo_setup']['repos']['value']:
            if repo_item['name'] in \
                    ('ubuntu', 'ubuntu-updates', 'ubuntu-security'):
                if self.cluster_settings.get('ubuntu_repository') != "none":
                    repo_item['uri'] = \
                        (str(self.cluster_settings.get('ubuntu_repository')))

        extra_repos = self.cluster_settings.get('extra_repositories', '')
        if extra_repos:
            existing_repos = attributes['editable']['repo_setup']['repos'][
                'value']
            for repo in extra_repos.splitlines():
                data = repo.strip().split()
                new_repo = {'name': data[0],
                            'type': data[1],
                            'uri': data[2],
                            'suite': data[3],
                            'section': ' '.join(data[4:-1]),
                            'priority': int(data[-1])}
                existing_repos.append(new_repo)

        if str(self.cluster_settings['operating_system']) == 'centos':
            centos_kernel = attributes['editable']['use_fedora_lt']['kernel']
            centos_kernel['value'] = u'fedora_lt_kernel'

        if 'neutron_advanced_configuration' in attributes['editable']:
            dvr = attributes['editable']['neutron_advanced_configuration']
            if 'value' in dvr['neutron_l2_pop']:
                if str(self.cluster_settings.get("net_segment_type")) != \
                        "vlan":
                    dvr['neutron_l2_pop']['value'] = True
            if 'value' in dvr['neutron_dvr']:
                if str(self.cluster_settings.get("dvr_enable")) == "true":
                    dvr['neutron_dvr']['value'] = True
                else:
                    dvr['neutron_dvr']['value'] = False

        if 'public_ssl' in attributes['editable']:
            public_ssl_enable = attributes['editable']['public_ssl']
            if 'value' in public_ssl_enable['horizon']:
                if str(self.cluster_settings.get("ssl_enable")) == "true":
                    public_ssl_enable['horizon']['value'] = True
                else:
                    public_ssl_enable['horizon']['value'] = False
            if 'value' in public_ssl_enable['services']:
                if str(self.cluster_settings.get("tls_enable")) == "true":
                    public_ssl_enable['services']['value'] = True
                else:
                    public_ssl_enable['services']['value'] = False

        if lma:
            editable_attr = attributes["editable"]
            collector_attr = editable_attr["lma_collector"]["metadata"]
            elastic_attr = editable_attr["elasticsearch_kibana"]["metadata"]
            influx_attr = editable_attr["influxdb_grafana"]["metadata"]

            collector_attr["enabled"] = True
            elastic_attr["enabled"] = True
            influx_attr["enabled"] = True

            collector_info = collector_attr["versions"][0]
            elastic_info = elastic_attr["versions"][0]
            influx_info = influx_attr["versions"][0]

            if self.cluster_settings.get('elasticsearch_server'):
                collector_info['elasticsearch_mode']['value'] = 'remote'
                collector_info["elasticsearch_address"]["value"] = \
                    self.cluster_settings.get('elasticsearch_server')
            else:
                elastic_info["jvm_heap_size"]["value"] = "8"
            if self.cluster_settings.get('influxdb_server'):
                collector_info['influxdb_mode']['value'] = 'remote'
                collector_info["influxdb_address"]["value"] = \
                    self.cluster_settings.get('influxdb_server')

            collector_info['environment_label']['value'] = \
                self.cluster_settings['env_name'] + "-" + str(uuid.uuid1())
            collector_info["influxdb_password"]["value"] = "r00tme"
            influx_info["influxdb_userpass"]["value"] = "r00tme"
            influx_info["influxdb_rootpass"]["value"] = "r00tme"
            influx_info["grafana_userpass"]["value"] = "r00tme"
            influx_info["mysql_password"]["value"] = "r00tme"
        client.update_cluster_attributes(cluster_id, attributes)

    def await_all_discovered_nodes(self, nodes, timeout=2000):
        """Wait for all discovered nodes."""
        nodes_count = len(nodes)
        logger.debug('Await {0} nodes discovering started'.format(nodes_count))
        client = NailgunClient(self.fuel_ip)

        nodes_macs = {}
        for node_name, node in nodes.iteritems():
            nodes_macs[node_name] = []
            for _, interface in node["interfaces"].iteritems():
                nodes_macs[node_name].append(interface["mac"])
        counter = 0
        while True:
            lost_nodes = nodes.keys()
            discovered_nodes = [k for k in client.list_nodes()
                                if not k['cluster'] and k['online'] and
                                k['status'] == 'discover']
            actual_kvm_count = len(discovered_nodes)
            logger.info(
                'Fuel discovered {0} nodes'.format(str(actual_kvm_count)))

            macs_found = set()
            for dnode in discovered_nodes:
                macs_found.update(iface['mac'].lower()
                                  for iface in dnode['meta']['interfaces'])

            for node, macs in nodes_macs.iteritems():
                for mac in macs:
                    if mac in macs_found:
                        lost_nodes.remove(node)
                        break

            if not lost_nodes:
                break

            logger.info('Lost nodes: {}'.format(lost_nodes))

            counter += 20
            if counter > timeout:
                raise RuntimeError('Waiting nodes timeout')
            time.sleep(20)

    def add_all_discovered_nodes_to_cluster(self,
                                            only_compute=False):
        """Add all available nodes to cluster."""
        client = NailgunClient(self.fuel_ip)
        cluster_id = client.get_cluster_id(self.cluster_settings['env_name'])
        all_nodes = []
        mac_list = self.cluster_settings['controller_mac_list']
        mac_list = [mac.strip() for mac in mac_list.split(';')]
        logger.debug('Nodes with %s will be assigned as controllers', mac_list)
        node_configs = json.loads(self.generate_nodes_config(
            only_compute))

        iter_cnt = (k for k in node_configs["controllers"])
        iter_cmp = (k for k in node_configs["computes"])
        iter_lma = (k for k in node_configs["lma"])
        for node in client.list_nodes():
            if node['cluster'] or not node['online']:
                continue
            if node['mac'] in mac_list:
                logger.debug('Node %s has been assigned as controller',
                             node['mac'])
                node_name = next(iter_cnt, None)
                if node_name is None:
                    continue
                params = node_configs["controllers"][node_name]
            else:
                logger.debug('Node %s has been assigned as compute',
                             node['mac'])
                node_name = next(iter_cmp, None)
                if node_name is None:
                    node_name = next(iter_cnt, None)
                    if node_name is None:
                        node_name = next(iter_lma, None)
                        if node_name is None:
                            continue
                        params = node_configs["lma"][node_name]
                    else:
                        params = node_configs["controllers"][node_name]
                else:
                    params = node_configs["computes"][node_name]

            data = {"cluster_id": cluster_id,
                    "pending_roles": params['roles'],
                    "pending_addition": True,
                    "name": node_name,
                    }
            client.update_node(node['id'], data)
            all_nodes.append(node)

        net_configuration = client.get_networks(cluster_id)
        default_nets = {net['name']: {'name': net['name'], 'id': net['id']}
                        for net in net_configuration['networks']}

        # Move networks on interfaces
        logger.debug('Move networks on interfaces')
        for node in client.list_cluster_nodes(cluster_id):
            controller = node['mac'] in mac_list
            self.update_node_networks(client, node['id'], controller,
                                      default_nets)

        # Update network
        logger.debug('Update network settings on cluster')
        if not only_compute:
            networks = self.generate_network_config()

            change_dict = networks.get('networking_parameters', {})
            for key, value in change_dict.items():
                net_configuration['networking_parameters'][key] = value

            for net in net_configuration['networks']:
                change_dict = networks.get(net['name'], {})
                for key, value in change_dict.items():
                    if key in net:
                        net[key] = value

            client.update_network(cluster_id,
                                  net_configuration['networking_parameters'],
                                  net_configuration['networks'])

        # update partition size on system disk
        for node in client.list_cluster_nodes(cluster_id):
            if 'controller' in node['pending_roles']:
                disks = client.get_node_disks(node['id'])
                base_disk = [disk for disk in disks if
                             any([volume for volume in disk['volumes']
                                  if volume['name'] == 'os' and
                                  volume['size'] > 0])]
                second_disk = [disk for disk in disks if
                               any([volume for volume in disk['volumes']
                                    if volume['name'] == 'os' and
                                    volume['size'] == 0])]
                third_disk = [disk for disk in disks if disk['name'] == 'sdc']
                base_disk = base_disk[0]
                if len(second_disk) > 0:
                    second_disk = second_disk[0]
                if len(third_disk) > 0:
                    third_disk = third_disk[0]
                volumes = base_disk['volumes']
                if len(second_disk) > 0:
                    second_volumes = second_disk['volumes']
                else:
                    second_volumes = []
                if len(third_disk) > 0:
                    third_volumes = third_disk['volumes']
                else:
                    third_volumes = []
                disk_size = base_disk['size']

                # For lab mirantis-1
                if self.lab_name == "mirantis-1":
                    # first disk used only for base system
                    for volume in volumes:
                        if volume['name'] == 'os':
                            volume['size'] = disk_size
                        else:
                            volume['size'] = 0
                    for second_volume in second_volumes:
                        if second_volume['name'] == 'mysql':
                            second_volume['size'] = 100000
                        elif second_volume['name'] == 'image':
                            second_volume['size'] = 100000
                        elif second_volume['name'] == 'mongo':
                            second_volume['size'] = 200000
                        elif second_volume['name'] == 'horizon':
                            second_volume['size'] = 13000
                        elif (second_volume['name'] == 'logs' and
                              len(third_disk) == 0):
                            second_volume['size'] = 500000
                        else:
                            second_volume['size'] = 0
                    for third_volume in third_volumes:
                        if third_volume['name'] == 'logs':
                            third_volume['size'] = 1000000
                        else:
                            third_volume['size'] = 0
                # For lab rackspace-1
                if self.lab_name == "rackspace-1":
                    for volume in volumes:
                        if volume['name'] == 'os':
                            volume['size'] = 512000
                        elif volume['name'] == 'mysql':
                            volume['size'] = 1024000
                        elif volume['name'] == 'image':
                            volume['size'] = 100000
                        elif volume['name'] == 'mongo':
                            volume['size'] = 100000
                        elif volume['name'] == 'horizon':
                            volume['size'] = 13000
                        elif volume['name'] == 'logs':
                            volume['size'] = 1024000
                        else:
                            volume['size'] = 0
                client.put_node_disks(node['id'], disks)
        return all_nodes

    def deploy_environment(self):
        client = NailgunClient(self.fuel_ip)
        cluster_id = client.get_cluster_id(self.cluster_settings['env_name'])
        no_ooops = True
        try:
            client.deploy_cluster_changes(cluster_id)
        except urllib2.HTTPError as err:
            if err.code == 504:
                logger.error(
                    'Oooops https://bugs.launchpad.net/fuel/+bug/1384623'
                    ' again')
                no_ooops = False
                time.sleep(30)
                return True
            else:
                raise RuntimeError(err)
        return no_ooops

    def update_node_networks(self, client, node_id, controller, net_list):
        pxe_nets = ['fuelweb_admin', 'management', 'storage']
        interfaces = client.get_node_interfaces(node_id)
        pxe_bus_id = next(iface['bus_info'] for iface in interfaces
                          if iface['pxe'])
        # pxe_bus_id = pxe_bus_id.split('.')[0]  # getting device bus id
        gig_ifaces = filter(lambda x: x['max_speed'] == 1000, interfaces)
        ten_gig_ifaces = filter(lambda x: x['max_speed'] == 10000, interfaces)

        # For lab mirantis-1
        if self.lab_name == "mirantis-1":
            # Networks layout:
            # Admin, Management and Storage: PXE interface (1st 10G NIC)
            # Public: 1st 1G NIC port
            # Private: Last 10G NIC port
            # On dedicated controllers in 10 env PXE and Private interfaces are
            # on different physical 10G NICS
            if controller:
                tgifaces = [iface for iface in ten_gig_ifaces if not
                            iface["bus_info"].startswith(
                                pxe_bus_id.split(".")[0])]
                if not tgifaces:
                    logger.warning(
                        "Same bus problem: node %s, ifaces %s, bus_id %s",
                        node_id, interfaces, pxe_bus_id)
                    tgifaces = [iface for iface in ten_gig_ifaces
                                if not iface["bus_info"].startswith(
                                    pxe_bus_id)]

                ten_gig_ifaces = tgifaces
            first_1g = min(gig_ifaces, key=lambda x: x['bus_info'])
            try:
                last_10g = max(ten_gig_ifaces, key=lambda x: x['bus_info'])
            except Exception:
                logger.debug("client: %s, interfaces: %s, controller: %s",
                             client,
                             interfaces, controller)
                raise

            for interface in interfaces:
                if interface['pxe']:
                    interface['assigned_networks'] = [
                        net_list[name] for name in pxe_nets]
                elif interface['name'] == first_1g['name']:
                    interface['assigned_networks'] = [net_list['public']]
                elif interface['name'] == last_10g['name']:
                    interface['assigned_networks'] = [net_list['private']]
                else:
                    interface['assigned_networks'] = []

                if interface['max_speed'] == 10000:
                    interface['interface_properties'] = {"mtu": "9000"}

        # For lab rackspace-1
        if self.lab_name == "rackspace-1":
            # ten_gig_ifaces = ['ens1f0', 'ens1f1', 'ens4f0', 'ens4f1']
            # Networks layout:
            # Storage and Private - bond0={ens1f1+ens4f1}
            # Admin and Public - ens1f0
            # Management - ens4f0
            interfaces.append({"type": "bond",
                               "name": "bond0",
                               "mode": "802.3ad",
                               "assigned_networks": [],
                               "bond_properties": {
                                   "mode": "802.3ad",
                                   "type__": "linux",
                                   "xmit_hash_policy": "layer3+4",
                                   "lacp_rate": "fast"},
                               "slaves": [
                                   {"name": "ens1f1"},
                                   {"name": "ens4f1"}]})

            for interface in interfaces:
                if interface['name'] == 'ens1f0':
                    interface['assigned_networks'] = \
                        [net_list['fuelweb_admin'], net_list['public']]
                elif interface['name'] == 'ens4f0':
                    interface['assigned_networks'] = [net_list['management']]
                elif interface['name'] == 'bond0':
                    interface['assigned_networks'] = [net_list['storage'],
                                                      net_list['private']]
                else:
                    interface['assigned_networks'] = []

        client.put_node_interfaces(node_id, interfaces)

    def await_deploy(self, all_nodes, timeout=10800):
        client = NailgunClient(self.fuel_ip)
        cluster_id = client.get_cluster_id(self.cluster_settings['env_name'])
        logger.debug('Await deploy started.')
        timer = 0
        status = 'deployment'
        time.sleep(180)
        no_oooops = True
        while timer < timeout and status != 'operational':
            time.sleep(120)
            timer += 120
            nodes_in_deploy = [k for k in client.list_nodes()
                               if str(k['status']).startswith('deploying')]
            logger.debug('{} nodes in deploy'.format(nodes_in_deploy))
            if len(nodes_in_deploy) > 50:
                logger.error('Oooops {0} nodes in deploy !'.format(
                    len(nodes_in_deploy)))
                # no_oooops = False
            if status not in ("deployment", "partially_deployed"):
                raise RuntimeError('Something went wrong with cluster deploy. '
                                   'Cluster status is {0}'.format(status))
            status = client.get_cluster(cluster_id)['status']
            logger.debug('Cluster status is {0}. Waiting {1} sec'.
                         format(status, timer))
        ready_nodes = len([k for k in client.list_nodes()
                           if str(k['status']).startswith('ready')])

        if all_nodes != ready_nodes:
            logger.error('Oooops not all nodes deployed ! '
                         'We are waiting {0} nodes but actually '
                         'have {1} nodes'.format(all_nodes, ready_nodes))
            no_oooops = False
        if timer >= timeout:
            raise RuntimeError('Waiting cluster timeout')
        return no_oooops

    def network_verify(self, timeout=3800):
        client = NailgunClient(self.fuel_ip)
        cluster_id = client.get_cluster_id(self.cluster_settings['env_name'])
        timer = 0
        task = {"status": "running"}
        while timer < timeout and task["status"] == "running":
            try:
                network_verification_task = client.verify_networks(cluster_id)
                task['status'] = ''
            except urllib2.HTTPError as err:
                if err.code == 400:
                    logger.warning(
                        'Another network verification running, waiting '
                        '30 seconds, {0} seconds '
                        'left'.format(timeout - timer))
                    time.sleep(30)
                    timer += 30
                else:
                    raise RuntimeError(err)
        if timer >= timeout:
            raise RuntimeError("Can't start network verification")
        timer = 0
        task = client.get_task(network_verification_task['id'])
        while timer < timeout and task['status'] != 'ready':
            logger.warning('Network verifications is not ready, '
                           'waiting 60 seconds')
            time.sleep(60)
            timer += 60
            task = client.get_task(network_verification_task['id'])
            logger.debug(task)
            if task['status'] == 'error':
                logger.error("Something goes wrong with network verification "
                             "status is {0}".format(task))
                return False
        if timer >= timeout:
            raise RuntimeError("Timeout waiting network verification")
        logger.debug('Network verification successful')
        return True

    def generate_nodes_config(self, only_compute=False,
                              local_cluster_settings=None):
        if not local_cluster_settings:
            local_cluster_settings = self.cluster_settings
        controller = ["controller"]
        compute = ["compute"]
        compute_cinder = ['compute', 'cinder']
        ceph = False
        lma = False
        d = {"controllers": {}, "computes": {}, "lma": {}}
        cnt_count = int(local_cluster_settings.get('controller_count'))
        cmp_count = int(local_cluster_settings.get('compute_count'))

        if local_cluster_settings.get('ceilometer', 'false') == 'true':
            controller.append("mongo")

        if local_cluster_settings.get("lma") == "true":
            lma = True

        for option in local_cluster_settings.viewkeys():
            if "ceph" in option:
                if local_cluster_settings.get(option) == "true":
                    ceph = True
                    break

        if not only_compute:
            for i in xrange(cnt_count):
                s = "controller_%d" % i
                d["controllers"].update({s: {"manufacturer": "QEMU"}})
                d["controllers"][s]["roles"] = controller
        for i in xrange(cmp_count):
            if only_compute:
                s = "compute_2{0}".format(int(os.urandom(2).encode('hex'), 16))
            else:
                s = "compute_%d" % i
            d["computes"].update({s: {"manufacturer": "QEMU"}})
            if local_cluster_settings.get('volumes_lvm') == "true":
                d["computes"][s]["roles"] = compute_cinder
            else:
                d["computes"][s]["roles"] = compute

        if ceph:
            ceph_count = int(local_cluster_settings.get('ceph_count'))
            for i in xrange(ceph_count):
                s = "compute_%d" % i
                d["computes"][s]["roles"] = compute + ["ceph-osd"]

        if lma and not local_cluster_settings.get('influxdb_server') and \
                not local_cluster_settings.get('elasticsearch_server'):
            d["lma"].update({"elasticsearch": {"manufacturer": "QEMU"}})
            d["lma"]["elasticsearch"]["roles"] = ["elasticsearch_kibana"]
            d["lma"].update({"influxdb": {"manufacturer": "QEMU"}})
            d["lma"]["influxdb"]["roles"] = ["influxdb_grafana"]
        elif lma and local_cluster_settings.get('elasticsearch_server') and \
                not local_cluster_settings.get('influxdb_server'):
            d["lma"].update({"influxdb": {"manufacturer": "QEMU"}})
            d["lma"]["influxdb"]["roles"] = ["influxdb_grafana"]
        elif lma and \
                not local_cluster_settings.get('elasticsearch_server') and \
                local_cluster_settings.get('influxdb_server'):
            d["lma"].update({"elasticsearch": {"manufacturer": "QEMU"}})
            d["lma"]["elasticsearch"]["roles"] = ["elasticsearch_kibana"]

        return str(json.dumps(d))

    def generate_network_config(self):
        networks = {}
        cidr = self.cluster_settings.get("cidr")
        mask = netaddr.IPNetwork(cidr).netmask
        net_size = int(netaddr.IPNetwork(cidr).prefixlen)
        public_start = self.cluster_settings.get("public_range").split('-')[0]
        public_end = self.cluster_settings.get("public_range").split('-')[1]
        floating_start = self.cluster_settings.get("floating_range"). \
            split('-')[0]
        floating_end = self.cluster_settings.get("floating_range"). \
            split('-')[1]

        networks["public"] = {
            "network_size": net_size,
            "netmask": "%s" % mask,
            "ip_ranges": [["%s" % public_start,
                           "%s" % public_end]],
            "cidr": "%s" % cidr,
            "gateway": self.cluster_settings.get("gateway")
        }
        if self.cluster_settings.get("public_vlan"):
            networks["public"]["vlan_start"] = int(
                self.cluster_settings.get("public_vlan"))
        networks["management"] = {}
        if int(self.cluster_settings.get("management_vlan")):
            networks["management"]["vlan_start"] = int(self.cluster_settings.
                                                       get("management_vlan"))
        if self.cluster_settings.get("management_network"):
            networks["management"]["cidr"] = self.cluster_settings.\
                get("management_network")

        networks["storage"] = {}
        if int(self.cluster_settings.get("storage_vlan")):
            networks["storage"]["vlan_start"] = int(self.cluster_settings.
                                                    get("storage_vlan"))
        if self.cluster_settings.get("storage_network"):
            networks["storage"]["cidr"] = self.cluster_settings.\
                get("storage_network")

        networks["networking_parameters"] = \
            {"floating_ranges": [[floating_start, floating_end]],
             "internal_cidr": "192.168.108.0/22"}

        if self.cluster_settings.get("net_segment_type") == "vlan":
            floating_vlan_start = \
                self.cluster_settings.get("floating_vlan_range").split('-')[0]
            floating_vlan_end = \
                self.cluster_settings.get("floating_vlan_range").split('-')[1]
            networks["networking_parameters"]["vlan_range"] = \
                [int(floating_vlan_start), int(floating_vlan_end)]

        if self.cluster_settings.get("net_segment_type") in ["gre", "tun"]:
            floating_vlan_start = \
                self.cluster_settings.get("floating_vlan_range").split('-')[0]
            networks["private"] = {
                "vlan_start": int(floating_vlan_start),
                "render_type": "cidr",
                "cidr": self.cluster_settings.get("private_network")
            }

        if self.cluster_settings.get("net_provider") == "nova_network":
            nn_floating_vlan = self.cluster_settings.get("nn_floating_vlan")
            networks["networking_parameters"]["fixed_networks_vlan_start"] = \
                int(nn_floating_vlan)
        logger.debug('Network setting is:{}'.format(networks))
        return networks

    def generate_components_config(self):
        settings = dict()
        settings["sahara"] = s2b(self.cluster_settings.get('sahara', 'false'))
        settings["murano"] = s2b(self.cluster_settings.get('murano', 'false'))
        settings["ceilometer"] = s2b(self.cluster_settings.get('ceilometer',
                                                               'false'))
        settings["volumes_lvm"] = s2b(self.cluster_settings.get('volumes_lvm',
                                                                'false'))
        settings["volumes_ceph"] = s2b(
            self.cluster_settings.get('volumes_ceph', 'false'))
        settings["images_ceph"] = s2b(self.cluster_settings.get('images_ceph',
                                                                'false'))
        settings["ephemeral_ceph"] = s2b(
            self.cluster_settings.get('ephemeral_ceph',
                                      'false'))
        settings["objects_ceph"] = s2b(
            self.cluster_settings.get('objects_ceph', 'false'))
        settings["osd_pool_size"] = '3'
        return settings


def s2b(v):
    return v.lower() in ("yes", "true", "t", "1")
