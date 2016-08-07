import logging

from drivers import NODES_INFO_DRIVER_FABRIC


class NodesInfoManager(object):
    def __init__(self, driver_type, connection_string):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        try:
            driver = NODES_INFO_DRIVER_FABRIC[driver_type]
        except Exception:
            logging.error("Can't find nodes_info manager driver {}".format(
                driver_type))
            raise

        self.driver = driver(connection_string)

    def get_env_info(self, env_name):
        env_info = self.driver.get_env_info(env_name)
        if not env_info:
            raise Exception

        return env_info

    def get_nodes_by_env(self, env_name):
        self.logger.debug('Try to get nodes from env {}'.format(env_name))

        nodes = self.driver.get_nodes_by_env(env_name)

        if nodes is None:
            self.logger.erro("Can't get nodes assigned to env {}".format(
                env_name))
            raise Exception

        return nodes

    def assign_nodes_to_env(self, nodes, env_name):
        self.logger.debug("Try to assign nodes {} to env {}".
                          format(",".join(nodes.keys()), env_name))

        if not self.driver.assign_nodes_to_env(nodes, env_name):
            self.logger.error("Can't assign nodes {} to env {}".
                              format(",".join(nodes.keys()), env_name))
            raise Exception
