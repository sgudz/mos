# -*- coding: utf-8 -*-
import common

import sqlalchemy.orm as orm

import clusterdb as db


class DeallocateServersApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "deallocate-servers",
            description="Deallocate servers from their environments.")

        parser.add_argument(
            "--power-off",
            help="Turn servers off after deallocating",
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
        super(DeallocateServersApp, self).__init__(options)

        self.names = list(set(options.names))
        self.power_off = options.power_off
        self.configure_switches = options.configure_switches

    def do(self):
        session = self.session_maker()

        servers = session.query(db.Server)
        servers = servers.options(orm.joinedload(db.Server.allocated_env))
        servers = servers.filter(db.Server.name.in_(self.names))
        servers = list(servers)

        if self.configure_switches:
            environment = session.query(db.Environment)
            environment = environment.filter(db.Environment.type == "ovs")
            environment = environment.first()
            environment.deallocate(servers)

        for srv in servers:
            srv.allocated_env = None
            session.merge(srv)
        session.commit()

        if self.power_off:
            for srv in servers:
                srv.power_off()
