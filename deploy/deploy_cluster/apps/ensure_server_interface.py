# -*- coding: utf-8 -*-


import common

import clusterdb as db


class EnsureServerInterfaceApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "ensure-server-interface",
            description=(
                "Ensure that server interface for given server "
                "has following parameters."))

        parser.add_argument(
            "--mac",
            required=True,
            help="MAC address of the interface.")
        parser.add_argument(
            "--port",
            help="Port on the switch where interface is connected.",
            default=None)
        parser.add_argument(
            "--switch-ip",
            help="IP address of the switch.")

        parser.add_argument(
            "server_name",
            metavar="SERVER_NAME",
            help="The name of the server with interface.")
        parser.add_argument(
            "interface_name",
            metavar="INTERFACE_NAME",
            help="The name of the interface on the server.")

        return parser

    def __init__(self, options):
        super(EnsureServerInterfaceApp, self).__init__(options)

        self.mac = options.mac
        self.port = options.port
        self.switch_ip = options.switch_ip
        self.server_name = options.server_name
        self.interface_name = options.interface_name

    def do(self):
        session = self.session_maker()

        server = session.query(db.Server) \
            .filter(db.Server.name == self.server_name) \
            .first()
        if not server:
            raise ValueError("Unknown server {}".format(self.server_name))

        interface = db.get_or_create(
            session, db.ServerInterface,
            server_id=server._id, name=self.interface_name)

        interface.name = self.interface_name
        interface.mac = self.mac
        interface.switch_ip = self.switch_ip
        interface.port = self.port or None

        session.add(interface)
        session.commit()
