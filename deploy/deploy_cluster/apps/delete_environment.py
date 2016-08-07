# -*- coding: utf-8 -*-


import common

import clusterdb as db


class DeleteEnvironmentApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "delete-environment", description="Delete environment.")

        parser.add_argument(
            "numbers",
            metavar="NUMBER",
            nargs="+",
            help="Environment number.",
            type=int)

        return parser

    def __init__(self, options):
        super(DeleteEnvironmentApp, self).__init__(options)

        self.numbers = list(set(options.numbers))

    def do(self):
        session = self.session_maker()

        environments = session.query(db.Environment) \
            .filter(db.Environment._id.in_(self.numbers)) \
            .all()

        for env in environments:
            session.delete(env)
            env.deallocate()

        session.commit()
