# -*- coding: utf-8 -*-


import common

import clusterdb as db


class DeleteServerApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "delete-server",
            description="Delete server from database")

        parser.add_argument(
            "names",
            metavar="SERVER_NAME",
            nargs="+",
            help="The name of the server.")

        return parser

    def __init__(self, options):
        super(DeleteServerApp, self).__init__(options)

        self.names = list(set(options.names))

    def do(self):
        session = self.session_maker()

        session.query(db.Server) \
            .filter(db.Server.name.in_(self.names)) \
            .delete(synchronize_session=False)

        session.commit()
