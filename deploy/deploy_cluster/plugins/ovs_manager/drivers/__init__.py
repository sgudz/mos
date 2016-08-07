from base_ovs_driver import BaseOVSDriver
from ovs_over_ssh_driver import OVSOverSSHDriver

OVS_DRIVER_FABRIC = {
    "ovs_over_ssh": OVSOverSSHDriver
}

for driver_name in OVS_DRIVER_FABRIC:
    driver = OVS_DRIVER_FABRIC[driver_name]
    if not issubclass(driver, BaseOVSDriver):
        raise ImportError("Driver {} should inherit "
                          "from BasePowerDriver".format(driver_name))
