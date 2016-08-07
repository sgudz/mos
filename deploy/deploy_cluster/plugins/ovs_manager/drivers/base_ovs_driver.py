class BaseOVSDriver(object):
    def add_block_rules_for_macs(self, mac_list):
        raise NotImplementedError("Should have implemented this")

    def add_permit_rules_for_macs(self, mac_list, vm_pxe_server_name):
        raise NotImplementedError("Should have implemented this")
