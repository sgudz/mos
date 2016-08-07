import os
import logging
from configparser import ConfigParser
from configparser import NoSectionError
from time import sleep

from plugins.nodes_info_manager import NodesInfoManager
from plugins.power_manager import PowerManager
from plugins.switch_manager import SwitchManager
from plugins.fuel_manager import FuelManager
from plugins.ovs_manager import OVSManager

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class DeployCluster(object):
    def __init__(self,
                 env_name,
                 connection_string,
                 cluster_settings,
                 fuel_ip,
                 lab_name,
                 delete_only,
                 configure_only,
                 configure_switches,
                 ovs_servers,
                 power_on_delay):
        self.env_name = env_name
        self.connection_string = connection_string
        self.cluster_settings = cluster_settings
        self.fuel_ip = fuel_ip
        self.lab_name = lab_name
        self.configure_switches = configure_switches
        self.configure_only = configure_only
        self.delete_only = delete_only
        self.power_on_delay = power_on_delay

        self.nodes_info_manager = NodesInfoManager(
            driver_type="database",
            connection_string=self.connection_string)
        self.env_info = self.nodes_info_manager.get_env_info(env_name)

        if self.configure_switches:
            self.switch_username = ""
            self.switch_password = ""
            self.switch_driver = ""
            self.switch_vlan = ""
            self.switch_manager = SwitchManager()

        self.configure_ovs = True if self.env_info["ovs_driver"] else False
        if self.configure_ovs:
            self.ovs_manager = OVSManager(self.env_info["ovs_driver"],
                                          ovs_servers)
            self.vm_pxe_server_name = self.env_info["vm_pxe_server_name"]

        self.fuel_manager = FuelManager(self.cluster_settings, self.fuel_ip,
                                        self.lab_name)
        self.power_manager = PowerManager()

    def run(self):
        nodes = self.nodes_info_manager.get_nodes_by_env(self.env_name)
        self.power_off_nodes(nodes)
        self.erase_env(nodes)
        if not self.delete_only:
            self.setup_env(nodes, self.env_name)
            logger.debug('SLEEP BEFORE POWER ON')
            sleep(15)
            self.power_on_nodes(nodes)
            self.fuel_manager.await_all_discovered_nodes(nodes)
            self.fuel_manager.add_all_discovered_nodes_to_cluster()

            if not self.configure_only:
                self.deploy_env(nodes)

    def deploy_env(self, nodes):
        deploy_results_status = self.fuel_manager.deploy_environment()
        await_results_status = self.fuel_manager.await_deploy(len(nodes))
        network_verify_status = True
        if self.cluster_settings.get('network_verification') == 'true':
            network_verify_status = self.fuel_manager.network_verify()
        if (not deploy_results_status or not await_results_status or
                not network_verify_status):
            raise RuntimeError("OMG ooops found ! I can't live, bye.")

    def erase_env(self, nodes):
        self.nodes_info_manager.assign_nodes_to_env(nodes, None)
        if self.configure_switches:
            self.setup_switches(nodes, "remove")
        if self.configure_ovs:
            mac_list = []
            for _, node in nodes.iteritems():
                for _, interface in node["interfaces"].iteritems():
                    mac_list.append(interface["mac"])
            self.ovs_manager.add_block_rules_for_macs(mac_list)
        self.fuel_manager.delete_environment()

    def setup_env(self, nodes, env_name):
        self.nodes_info_manager.assign_nodes_to_env(nodes, env_name)

        if self.configure_switches:
            self.setup_switches(nodes, "add")

        if self.configure_ovs:
            mac_list = []
            for _, node in nodes.iteritems():
                for _, interface in node["interfaces"].iteritems():
                    mac_list.append(interface["mac"])
            self.ovs_manager.add_permit_rules_for_macs(mac_list,
                                                       self.vm_pxe_server_name)

        self.fuel_manager.create_environment()

    def setup_switches(self, nodes, action):
        for _, node in nodes.iteritems():
            for interface in node["interfaces"].iteritems():
                if action == "remove":
                    self.switch_manager.remove_ports_from_vlan(
                        self.switch_driver,
                        interface["switch_ip"],
                        self.switch_username,
                        self.switch_password,
                        self.switch_vlan,
                        interface["port"]
                    )
                elif action == "add":
                    self.switch_manager.add_ports_to_vlan(
                        self.switch_driver,
                        interface["switch_ip"],
                        self.switch_username,
                        self.switch_password,
                        self.switch_vlan,
                        interface["port"]
                    )
                else:
                    raise Exception("Unknown switch action: {}".format(action))

    def power_off_nodes(self, nodes):
        config = ConfigParser()
        config_file = "{}/etc/env.conf".format(
            os.path.dirname(os.path.realpath(__file__)))
        config.read(config_file)
        try:
            username = config.get('main', 'ipmi_user')
        except Exception as error:
            logging.error(("Can't get power_manager user from "
                           "config file {}: {}").format(
                config_file, error))
            raise
        for _, node in nodes.iteritems():
            self.power_manager.power_off(node["ip"],
                                         node["name"],
                                         username,
                                         node["password"],
                                         node["power_driver"])

    def power_on_nodes(self, nodes):
        config = ConfigParser()
        config_file = "{}/etc/env.conf".format(
            os.path.dirname(os.path.realpath(__file__)))
        config.read(config_file)
        try:
            username = config.get('main', 'ipmi_user')
        except Exception as error:
            logging.error(("Can't get power_manager user from "
                           "config file {}: {}").format(
                config_file, error))
            raise

        for _, node in nodes.iteritems():
            self.power_manager.power_on(node["ip"],
                                        node["name"],
                                        username,
                                        node["password"],
                                        node["power_driver"])
            sleep(self.power_on_delay)


def main():
    parser = ConfigParser()
    current_path = (os.path.dirname(os.path.realpath(__file__)))
    parser.read('{0}/etc/env.conf'.format(current_path))

    cluster_settings = dict(parser.items('cluster'))
    env_settings = dict(parser.items('env'))
    main_settings = dict(parser.items("main"))

    database_path = main_settings.get("database", "sqlite:////tmp/database.db")
    env_name = env_settings.get('env_number')
    fuel_ip = env_settings.get('fuel_ip')
    delete_env = env_settings.get('delete_env') == "true"
    configure_only = env_settings.get('configure_only') == "true"
    configure_switches = env_settings.get('configure_switches') == "true"
    power_on_delay = int(env_settings.get("power_on_delay"))
    lab_name = cluster_settings.get("lab_name")

    try:
        ovs_settings = dict(parser.items("ovs_switches"))
        ovs_servers_ips = ovs_settings.get("switches").split(",")
        ovs_servers_username = ovs_settings.get("username")
        ovs_servers_password = ovs_settings.get("password")
        ovs_servers = {}
        for ovs_server in ovs_servers_ips:
            ovs_servers[ovs_server] = {"username": ovs_servers_username,
                                       "password": ovs_servers_password}
    except NoSectionError:
        ovs_servers = {}

    DeployCluster(env_name=env_name,
                  fuel_ip=fuel_ip,
                  connection_string=database_path,
                  cluster_settings=cluster_settings,
                  lab_name=lab_name,
                  delete_only=delete_env,
                  configure_only=configure_only,
                  configure_switches=configure_switches,
                  ovs_servers=ovs_servers,
                  power_on_delay=power_on_delay).run()

if __name__ == "__main__":
    main()
