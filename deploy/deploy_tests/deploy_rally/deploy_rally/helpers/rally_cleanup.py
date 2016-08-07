"""
Simple tool, which remove servers, subnets and networks based on name prefix

HOW-TO:
 1) login as developer user
 2) run this script

FIXME:
 use rally cleanup mechanism directly
"""

from rally import osclients

# TODO(andreykurilin): discover all prefixes from rally code and don't use
#                      such broad prefix
RALLY_NAME_PREFIX = "rally_"


def make_header(text, size=80, symbol="-"):
    """Unified way to make header message to CLI.

    :param text: what text to write
    :param size: Length of header decorative line
    :param symbol: What symbol to use to create header
    """
    header = symbol * size + "\n"
    header += " %s\n" % text
    header += symbol * size + "\n"
    return header


def main():
    clients = osclients.Clients.create_from_env()
    print(make_header("Start processing Nova resources."))
    print("Obtain Nova servers. Please way a moment...")
    servers = [
        s for s in clients.nova().servers.list(search_opts={"all_tenants": 1})
        if s.startswith(RALLY_NAME_PREFIX)]
    if servers:
        print("There are '%s' found servers. Start delete them\n" %
              len(servers))
        map(lambda server: server.delete(), servers)
    else:
        print("There is no servers with '%s' prefix." % RALLY_NAME_PREFIX)

    print(make_header("Start processing Neutron resources."))
    print("Obtain Neutron sub-networks. Please way a moment...")
    subnets = [sn for sn in clients.neutron().list_subnets()["subnets"]
               if sn["name"].startswith(RALLY_NAME_PREFIX)]
    if subnets:
        print("There are '%s' found sub-networks. Start delete them\n" %
              len(subnets))
        map(lambda sn: clients.neutron().delete_subnet(sn["id"]), subnets)
    else:
        print("There is no sub-networks with '%s' prefix." % RALLY_NAME_PREFIX)

    print("Obtain Neutron networks. Please way a moment...")
    nets = [net for net in clients.neutron().list_networks()["networks"]
            if net["name"].startswith(RALLY_NAME_PREFIX)]
    if nets:
        print("There are '%s' found networks. Start delete them\n" %
              len(subnets))
        map(lambda net: clients.neutron().delete_network(net["id"]), nets)
    else:
        print("There is no sub-networks with '%s' prefix." % RALLY_NAME_PREFIX)


if __name__ == '__main__':
    main()
