import logging

from drivers import POWER_DRIVER_FABRIC


class PowerManager(object):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def power_status(self, ip, name, username, password, driver_type):
        self.logger.debug('Try to get IPMI power status')

        driver = get_driver(driver_type)

        status = driver.power_status(ip, name, username, password)

        if status is None:
            self.logger.error("Can't get status of node {}".format(ip))
            raise Exception

        return status

    def power_off(self, ip, name, username, password, driver_type):
        self.logger.debug('Try to power off node {0}'.format(ip))

        driver = get_driver(driver_type)
        if not driver.power_off(ip, name, username, password):
            self.logger.error("Can't power off node {}".format(ip))
            raise Exception

    def power_on(self, ip, name, username, password, driver_type):
        self.logger.debug('Try to power on node {0}'.format(ip))

        driver = get_driver(driver_type)

        if not driver.power_on(ip, name, username, password):
            self.logger.error("Can't power on node {}".format(ip))
            raise Exception


def get_driver(driver_type):
    if driver_type in [None, "real"]:
        driver_type = "supermicro_ipmi"

    try:
        driver = POWER_DRIVER_FABRIC[driver_type]
    except Exception:
        logging.error("Can't find power_manager driver {}".format(driver_type))
        raise

    return driver()
