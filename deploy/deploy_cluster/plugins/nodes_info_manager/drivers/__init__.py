from base_nodes_info_driver import BaseNodesInfoDriver
from database_driver import DatabaseDriver

NODES_INFO_DRIVER_FABRIC = {
    "database": DatabaseDriver
}

for driver_name in NODES_INFO_DRIVER_FABRIC:
    driver = NODES_INFO_DRIVER_FABRIC[driver_name]
    if not issubclass(driver, BaseNodesInfoDriver):
        raise ImportError("Driver {} should inherit "
                          "from BaseNodesInfoDriver".format(driver_name))
