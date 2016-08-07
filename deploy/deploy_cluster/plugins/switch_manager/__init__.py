import logging

from drivers import SWITCH_DRIVER_FABRIC


class SwitchManager(object):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.drivers_cache = {}

    def remove_ports_from_vlan(self, driver_type, switch_ip, switch_username,
                               switch_password, vlan, ports):
        self.logger.debug('Start main remove_ports_from_vlan')
        if driver_type not in self.drivers_cache:
            try:
                driver = SWITCH_DRIVER_FABRIC[driver_type]
            except Exception:
                logging.error("Can't find switch manager driver {}".format(
                    driver_type))
                raise
            self.drivers_cache[driver_type] = driver()

        driver = self.drivers_cache[driver_type]

        driver.remove_ports_from_vlan(switch_ip, switch_username,
                                      switch_password, vlan, ports)

    def add_ports_to_vlan(self, driver_type, switch_ip, switch_username,
                          switch_password, vlan, ports):
        self.logger.debug('Start main add_ports_to_vlan')
        if driver_type not in self.drivers_cache:
            try:
                driver = SWITCH_DRIVER_FABRIC[driver_type]
            except Exception:
                logging.error("Can't find switch manager driver {}".format(
                    driver_type))
                raise
            self.drivers_cache[driver_type] = driver()

        driver = self.drivers_cache[driver_type]

        driver.add_ports_to_vlan(switch_ip, switch_username,
                                 switch_password, vlan, ports)
