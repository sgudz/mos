# -*- coding: utf-8 -*-


from deploy.deploy_cluster.plugins.power_manager.drivers import \
    supermicro_ipmi_driver
from deploy.deploy_cluster.plugins.switch_manager.drivers import \
    dell_switch_driver


class IPMI(supermicro_ipmi_driver.SuperMicroIPMI):

    def _read_config(self, *args, **kwargs):
        return "engineer"


class DellSwitch(dell_switch_driver.DellExtension):

    def __init__(self, *args, **kwargs):
        super(DellSwitch, self).__init__(False)
        self.password = "Fa#iR36cHE0"

    def _read_config(self):
        vlans = [10, 11, 12, 13, 14]
        switches = {
            "sw-de-1": {"ip": "172.16.42.10", "vendor": "dell", "vlans": {}},
            "sw-de-3": {"ip": "172.16.42.12", "vendor": "dell", "vlans": {}},
            "sw-de-5": {"ip": "172.16.42.15", "vendor": "dell", "vlans": {}},
            "sw-de-7": {"ip": "172.16.42.33", "vendor": "dell", "vlans": {}},
            "sw-de-9": {"ip": "172.16.42.37", "vendor": "dell", "vlans": {}},
            "sw-de-11": {"ip": "172.16.42.43", "vendor": "dell", "vlans": {}},
            "sw-de-13": {"ip": "172.16.42.45", "vendor": "dell", "vlans": {}}}

        return switches, vlans
