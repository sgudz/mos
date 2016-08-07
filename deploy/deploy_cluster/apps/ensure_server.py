# -*- coding: utf-8 -*-


import common

import clusterdb as db


class EnsureServerApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "ensure-server",
            description=(
                "Ensure that server is created "
                "and has following parameters."))

        parser.add_argument(
            "-i", "--node-ip",
            help="Node IP for IPMI.",
            default="")
        parser.add_argument(
            "-p", "--node-password",
            help="Node password for IPMI.",
            default="")
        parser.add_argument(
            "--default",
            help="Default environment for server.",
            default=None)
        parser.add_argument(
            "name",
            metavar="SERVER_NAME",
            help="The name of the server.")

        return parser

    def __init__(self, options):
        super(EnsureServerApp, self).__init__(options)

        self.name = options.name
        self.default = options.default
        self.password = options.node_password
        self.ip = options.node_ip

    def do(self):
        session = self.session_maker()

        server = db.get_or_create(session, db.Server, name=self.name)
        server.name = self.name
        server.node_ip = self.ip
        server.node_password = self.password

        if self.default:
            query = session.query(db.Environment)
            query = query.filter(db.Environment.name == self.default)
            env = query.first()

            if not env:
                raise ValueError(
                    "Unknown environment {} is used.".format(self.default))

            server.default_env = env

        session.add(server)
        session.commit()
