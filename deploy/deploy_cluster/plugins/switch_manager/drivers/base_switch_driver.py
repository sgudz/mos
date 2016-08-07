class BaseSwitchDriver(object):
    def remove_ports_from_vlan(self, switch_ip, switch_username,
                               switch_password, vlan, ports):
        raise NotImplementedError("Should have implemented this")

    def add_ports_to_vlan(self, switch_ip, switch_username,
                          switch_password, vlan, ports):
        raise NotImplementedError("Should have implemented this")
