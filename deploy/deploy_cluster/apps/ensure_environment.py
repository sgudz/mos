# -*- coding: utf-8 -*-


import common

import clusterdb as db


class EnsureEnvironmentApp(common.App):

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "ensure-environment",
            description=(
                "Ensure that environment is created and has "
                "following parameters."))
        parser.add_argument(
            "-t", "--env-type",
            help="Env type",
            choices=["vlan", "ovs"],
            default="")
        parser.add_argument(
            "name",
            metavar="NAME",
            help="Environment name.")
        parser.add_argument(
            "param",
            metavar="PARAM",
            help="VLAN or text parameter of the environment.")
        parser.add_argument(
            "capacity",
            metavar="CAPACITY",
            help="How many nodes does this environment has.",
            type=int)

        return parser

    def __init__(self, options):
        super(EnsureEnvironmentApp, self).__init__(options)

        self.name = options.name
        self.param = options.param
        self.capacity = options.capacity
        self.env_type = options.env_type

    def do(self):
        session = self.session_maker()

        env = db.get_or_create(session, db.Environment, name=self.name)
        env.name = self.name
        env.param = self.param
        env.capacity = self.capacity
        env.type = self.env_type

        session.add(env)
        session.commit()
