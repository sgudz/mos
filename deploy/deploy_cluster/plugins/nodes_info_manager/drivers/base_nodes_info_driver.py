class BaseNodesInfoDriver(object):
    def get_env_info(self, env_name):
        raise NotImplementedError("Should have implemented this")

    def get_nodes_by_env(self, env_name):
        raise NotImplementedError("Should have implemented this")

    def assign_nodes_to_env(self, nodes, env_name):
        raise NotImplementedError("Should have implemented this")
