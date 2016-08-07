# -*- coding: utf-8 -*-


import sqlalchemy.orm as orm
import clusterdb as db

import common


class ListServerApp(common.ListApp):

    observable = True

    CSV_FIELDS = (
        "name",
        "node_ip",
        "node_password",
        "allocated",
        "default",
        "interfaces_eth0_mac",
        "interfaces_eth0_port",
        "interfaces_eth0_vlan",
        "interfaces_eth0_switch_ip",
        "interfaces_eth2_mac",
        "interfaces_eth2_port",
        "interfaces_eth2_vlan",
        "interfaces_eth2_switch_ip",
        "interfaces_eth3_mac",
        "interfaces_eth3_port",
        "interfaces_eth3_vlan",
        "interfaces_eth3_switch_ip")

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "list-server", description="Fetch description on scale lab")

        parser.add_argument(
            "-e", "--env",
            help=(
                "Environment name. If nothing is set, then information "
                "about all environments will be shown"),
            type=int,
            default=None)
        parser.add_argument(
            "server_names",
            metavar="SERVER_NAME",
            nargs="*",
            help="Names of servers to show.")

        return parser

    @staticmethod
    def extract_interfaces(server):
        interfaces = {}

        for interface in server.interfaces:
            interfaces[interface.name] = {
                "mac": interface.mac,
                "port": interface.port,
                "vlan": interface.vlan,
                "switch_ip": interface.switch_ip
            }

        return interfaces

    def __init__(self, options):
        super(ListServerApp, self).__init__(options)

        self.env = options.env
        self.server_names = options.server_names

    def get_info(self):
        server_set = {}

        session = self.session_maker()
        query = session.query(db.Server)
        query = query.options(orm.joinedload(db.Server.interfaces))
        query = query.options(orm.joinedload(db.Server.allocated_env))
        query = query.options(orm.joinedload(db.Server.default_env))

        if self.env:
            env = session.query(db.Environment) \
                .filter(db.Environment.name == self.env).first()
            query = query \
                .filter(db.Server.allocated_env == env)

        if self.server_names:
            query = query.filter(db.Server.name.in_(self.server_names))

        servers = query.order_by(db.Server.name).all()
        servers = sorted(servers, key=lambda srv: (srv.env_no, srv.name))

        for server in servers:
            server_set[server.name] = {
                "node_ip": server.node_ip,
                "node_password": server.node_password,
                "interfaces": self.extract_interfaces(server),
                "allocated_to": getattr(server.allocated_env, "name", None),
                "default_env": getattr(server.default_env, "name", None)
            }

        return server_set

    def info_to_csv(self, info):
        for name, data in sorted(info.iteritems()):
            item = {
                "name": name,
                "node_ip": data["node_ip"],
                "node_password": data["node_password"],
                "allocated": data["allocated_to"] or "",
                "default": data["default_env"] or "",
            }

            item["interfaces_eth0_mac"] = self.get_csv_ifdata(
                data, "interfaces_eth0_mac")
            item["interfaces_eth0_port"] = self.get_csv_ifdata(
                data, "interfaces_eth0_port")
            item["interfaces_eth0_vlan"] = self.get_csv_ifdata(
                data, "interfaces_eth0_vlan")
            item["interfaces_eth0_switch_ip"] = self.get_csv_ifdata(
                data, "interfaces_eth0_switch_ip")

            item["interfaces_eth2_mac"] = self.get_csv_ifdata(
                data, "interfaces_eth2_mac")
            item["interfaces_eth2_port"] = self.get_csv_ifdata(
                data, "interfaces_eth2_port")
            item["interfaces_eth2_vlan"] = self.get_csv_ifdata(
                data, "interfaces_eth2_vlan")
            item["interfaces_eth2_switch_ip"] = self.get_csv_ifdata(
                data, "interfaces_eth2_switch_ip")

            item["interfaces_eth3_mac"] = self.get_csv_ifdata(
                data, "interfaces_eth3_mac")
            item["interfaces_eth3_port"] = self.get_csv_ifdata(
                data, "interfaces_eth3_port")
            item["interfaces_eth3_vlan"] = self.get_csv_ifdata(
                data, "interfaces_eth3_vlan")
            item["interfaces_eth3_switch_ip"] = self.get_csv_ifdata(
                data, "interfaces_eth3_switch_ip")

            yield item

    @staticmethod
    def get_csv_ifdata(data, line):
        value = data

        for chunk in line.split("_", 2):
            value = value.get(chunk, {})

        if value is data:
            return ""

        return value or ""
