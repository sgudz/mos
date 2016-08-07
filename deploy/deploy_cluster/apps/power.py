# -*- coding: utf-8 -*-


import common

import clusterdb as db


class PowerApp(common.ListApp):

    observable = True

    CSV_FIELDS = (
        "server",
        "environment",
        "ip",
        "password",
        "status")

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "power",
            description="Power servers.")

        parser.add_argument(
            "action",
            choices=("on", "off", "reset", "status"),
            help="What to do.")
        parser.add_argument(
            "server_names",
            metavar="SERVER_NAME",
            nargs="+",
            help="Names of servers to process.")

        return parser

    def __init__(self, options):
        super(PowerApp, self).__init__(options)

        if options.action == "on":
            self.action = {"on"}
        elif options.action == "off":
            self.action = {"off"}
        elif options.action == "reset":
            self.action = {"on", "off"}
        else:
            self.action = {}

        self.server_names = list(set(options.server_names))

    def get_servers(self, session):
        servers = session.query(db.Server)

        if self.server_names:
            servers = servers.filter(db.Server.name.in_(self.server_names))

        return list(servers)

    def power(self, poweron, servers):
        for srv in servers:
            if poweron:
                srv.power_on()
            else:
                srv.power_off()

        db.wait_server_status(poweron, servers)

    def do(self):
        session = self.session_maker()
        servers = self.get_servers(session)

        if "off" in self.action:
            self.power(False, servers)
        if "on" in self.action:
            self.power(True, servers)

        return super(PowerApp, self).do()

    def get_info(self):
        session = self.session_maker()
        servers = self.get_servers(session)
        info = {}

        for srv in servers:
            info[srv.name] = {
                "environment": getattr(srv.allocated_env, "name", None),
                "ip": srv.node_ip,
                "password": srv.node_password,
                "is_powered_on": srv.is_powered_on}

        return info

    def info_to_csv(self, info):
        csv_info = []

        for name, data in sorted(info.iteritems()):
            data["server"] = name
            csv_info.append(data)

        return csv_info
