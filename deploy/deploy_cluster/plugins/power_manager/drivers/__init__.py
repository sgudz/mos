from base_power_driver import BasePowerDriver
from supermicro_ipmi_driver import SuperMicroIPMIDriver
from nova_power_driver import NovaPowerDriver

POWER_DRIVER_FABRIC = {
    "supermicro_ipmi": SuperMicroIPMIDriver,
    "nova_api": NovaPowerDriver
}

for driver_name in POWER_DRIVER_FABRIC:
    driver = POWER_DRIVER_FABRIC[driver_name]
    if not issubclass(driver, BasePowerDriver):
        raise ImportError("Driver {} should inherit "
                          "from BasePowerDriver".format(driver_name))
