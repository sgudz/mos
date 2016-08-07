import logging
from time import sleep

from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient import client
from novaclient.exceptions import NotFound

from base_power_driver import BasePowerDriver

API_VERSION = "2.1"
USER_DOMAIN_ID = "default"
PROJECT_DOMAIN_ID = "default"
POWER_ACTION_TIMEOUT = 300


class NovaPowerDriver(BasePowerDriver):
    def __init__(self, log_level=logging.DEBUG):
        logging.basicConfig(level=log_level)
        self.logger = logging.getLogger(__name__)

        self.status_on_values = ["ACTIVE"]
        self.status_off_values = ["SHUTOFF"]

    def power_status(self, ip, name, username, password):
        user_data = username.split("/")
        if len(user_data) != 2:
            logging.error("Wrong parameter value")
            raise Exception

        project_name = user_data[0]
        os_username = user_data[1]

        nova_client = get_client(ip, project_name, os_username, password)

        try:
            server = nova_client.servers.find(name=name)
        except NotFound:
            self.logger.error("Node not found")
            raise

        status = server.status
        if status in self.status_on_values:
            return True
        elif status in self.status_off_values:
            return False
        else:
            self.logger.debug("Status of node is unknown")
            return None

    def power_off(self, ip, name, username, password):
        user_data = username.split("/")
        if len(user_data) != 2:
            self.logger.error("Wrong parameter value")
            raise Exception

        project_name = user_data[0]
        os_username = user_data[1]
        nova_client = get_client(ip, project_name, os_username, password)
        try:
            server = nova_client.servers.find(name=name)
        except NotFound:
            self.logger.error("Node not found")
            raise

        self.logger.info("Trying to power off node {}".format(name))
        if self.power_status(ip, name, username, password) is False:
            self.logger.info("Node {} already powered off. "
                             "Won't do it again".format(name))
            return True
        try:
            server.stop()
        except Exception:
            self.logger.error("Can't power off node {}".format(name))
            raise

        self.logger.debug("Wait while node {} is powered off".format(name))
        timer = 0
        while True:
            if self.power_status(ip, name, username, password) is False:
                break
            if timer > POWER_ACTION_TIMEOUT:
                self.logger.error("Exceed timeout while waiting when"
                                  " node {} is powered off".format(name))
                raise RuntimeError
            sleep(2)
            timer += 2

        return True

    def power_on(self, ip, name, username, password):
        user_data = username.split("/")
        if len(user_data) != 2:
            self.logger.error("Wrong parameter value")
            raise Exception

        project_name = user_data[0]
        os_username = user_data[1]
        nova_client = get_client(ip, project_name, os_username, password)

        try:
            server = nova_client.servers.find(name=name)
        except NotFound:
            logging.error("Node not found")
            raise

        self.logger.info("Trying to power on node {}".format(name))
        if self.power_status(ip, name, username, password) is True:
            self.logger.info("Node {} already powered on. "
                             "Won't do it again".format(name))
            return True
        try:
            server.start()
        except Exception:
            self.logger.error("Can't power on node {}".format(name))
            raise

        self.logger.debug("Wait while node is powered on")
        timer = 0
        while True:
            if self.power_status(ip, name, username, password) is True:
                break
            if timer > POWER_ACTION_TIMEOUT:
                self.logger.error("Exceed timeout while wait power is on")
                raise RuntimeError
            sleep(2)
            timer += 2

        return True


def get_client(ip, project_name, os_username, password):
    auth = v3.Password(auth_url=ip,
                       username=os_username,
                       password=password,
                       project_name=project_name,
                       user_domain_id=USER_DOMAIN_ID,
                       project_domain_id=PROJECT_DOMAIN_ID)

    sess = session.Session(auth=auth)

    return client.Client(API_VERSION, session=sess)
