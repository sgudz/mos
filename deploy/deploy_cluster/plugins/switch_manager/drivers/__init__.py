from base_switch_driver import BaseSwitchDriver

SWITCH_DRIVER_FABRIC = {
}

for driver_name in SWITCH_DRIVER_FABRIC:
    driver = SWITCH_DRIVER_FABRIC[driver_name]
    if not issubclass(driver, BaseSwitchDriver):
        raise ImportError("Driver {} should inherit "
                          "from BasePowerDriver".format(driver_name))
