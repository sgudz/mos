# -*- coding: utf-8 -*-


import common

import clusterdb as db


class DeleteServerInterfaceApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "delete-server-interface", description="Delete server interface.")

        parser.add_argument(
            "server_name",
            metavar="SERVER_NAME",
            help="The name of the server which has such interface.")
        parser.add_argument(
            "interface_name",
            metavar="INTERFACE_NAME",
            help="The name of the interface to delete.")

        return parser

    def __init__(self, options):
        super(DeleteServerInterfaceApp, self).__init__(options)

        self.server_name = options.server_name
        self.interface_name = options.interface_name

    def do(self):
        session = self.session_maker()

        server = session.query(db.Server) \
            .filter(db.Server.name == self.server_name) \
            .first()
        if not server:
            return

        query = session.query(db.ServerInterface)
        query = query.filter(db.ServerInterface.server == server)
        query = query.filter(db.ServerInterface.name == self.interface_name)

        query.delete(synchronize_session=False)
        session.commit()
