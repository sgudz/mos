# -*- coding: utf-8 -*-


import common

import sqlalchemy.orm as orm

import clusterdb as db


class AllocateServersApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "allocate-servers",
            description="Allocate servers to environments.")

        parser.add_argument(
            "environment_name",
            metavar="ENVIRONMENT_NAME",
            help="The number of environment to allocate to.")
        parser.add_argument(
            "--power-on",
            help="Power servers on by IPMI.",
            action="store_true",
            default=False)
        parser.add_argument(
            "--configure-switches",
            help="Configure switches for servers.",
            action="store_true",
            default=False)
        parser.add_argument(
            "names",
            metavar="SERVER_NAME",
            nargs="+",
            help="Server names.")

        return parser

    def __init__(self, options):
        super(AllocateServersApp, self).__init__(options)

        self.env_na = options.environment_name
        self.names = list(set(options.names))
        self.power_on = options.power_on
        self.configure_switches = options.configure_switches

    def do(self):
        session = self.session_maker()

        environment = session.query(db.Environment)
        environment = environment.filter(db.Environment.name == self.env_na)
        environment = environment.first()

        if not environment:
            raise ValueError(
                "Environment with name {} is not defined.".format(
                    self.env_na))

        servers = session.query(db.Server)
        servers = servers.options(orm.joinedload(db.Server.allocated_env))
        servers = servers.filter(db.Server.name.in_(self.names))
        servers = list(servers)

        absent_servers = []
        found_names = set(srv.name for srv in servers)

        for name in self.names:
            if name not in found_names:
                absent_servers.append(name)

        if absent_servers:
            raise ValueError(
                "Servers {} were not found!".format(
                    ", ".join(absent_servers)))

        for srv in servers:
            if srv.allocated_env:
                raise ValueError(
                    "Server {} allocated for env {}".format(
                        srv.name, srv.allocated_env.name))

        environment.allocate(servers, self.configure_switches)

        if self.power_on:
            for srv in servers:
                srv.power_on()

        session.commit()
