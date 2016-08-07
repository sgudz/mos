# -*- coding: utf-8 -*-


import sqlalchemy.orm as orm
import clusterdb as db

import common


class ListEnvironmentApp(common.ListApp):

    observable = True

    CSV_FIELDS = (
        "name",
        "vlan",
        "capacity",
        "default_servers",
        "allocated_servers")

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "list-environment", description="List environments.")

        return parser

    def get_info(self):
        session = self.session_maker()

        query = session.query(db.Environment)
        query = query.options(orm.joinedload(db.Environment.default_servers))
        query = query.options(orm.joinedload(db.Environment.allocated_servers))
        environments = query.order_by(db.Environment.name).all()

        env_data = {}
        for env in environments:
            env_data[env.name] = {
                "capacity": env.capacity,
                "param": env.param,
                "type": env.type,
                "default_servers": sorted(
                    srv.name for srv in env.default_servers),
                "allocated_servers": sorted(
                    srv.name for srv in env.allocated_servers)}

        return env_data

    def info_to_csv(self, info):
        for name, data in sorted(info.iteritems()):
            data["name"] = name
            data["default_servers"] = len(data["default_servers"])
            data["allocated_servers"] = len(data["allocated_servers"])

            yield data
