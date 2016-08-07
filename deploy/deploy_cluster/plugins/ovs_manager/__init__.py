import logging

from drivers import OVS_DRIVER_FABRIC


class OVSManager(object):
    def __init__(self, driver_type, ovs_servers):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        try:
            driver = OVS_DRIVER_FABRIC[driver_type]
        except Exception:
            logging.error("Can't find switch manager driver {}".format(
                driver_type))
            raise

        self.driver = driver(ovs_servers)

    def add_block_rules_for_macs(self, mac_list):
        self.logger.debug('Start main remove_ports_from_vlan')

        self.driver.add_block_rules_for_macs(mac_list)

    def add_permit_rules_for_macs(self, mac_list, vm_pxe_server_name):
        self.logger.debug('Start main add_ports_to_vlan')

        self.driver.add_permit_rules_for_macs(mac_list, vm_pxe_server_name)
