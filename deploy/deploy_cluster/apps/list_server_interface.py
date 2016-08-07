# -*- coding: utf-8 -*-


import common

import sqlalchemy.orm as orm

import clusterdb as db


class ListServerInterfaceApp(common.ListApp):

    observable = True

    CSV_FIELDS = (
        "server_name",
        "name",
        "mac",
        "port",
        "vlan",
        "switch_ip")

    @classmethod
    def create_parser(cls, parsers):
        parser = parsers.add_parser(
            "list-server-interface", description="List server interfaces.")

        parser.add_argument(
            "-i", "--if-name",
            help="The name of the interface to show.",
            default=None)
        parser.add_argument(
            "-s", "--switch-ip",
            help="IP address of connected switch.",
            default=None)
        parser.add_argument(
            "-p", "--port",
            help="Port on connected switch.",
            default=None)
        parser.add_argument(
            "-m", "--mac-address",
            help="MAC address of network interface.",
            default=None)
        parser.add_argument(
            "-l", "--vlan",
            help="VLAN for network interface.",
            type=int,
            default=None)
        parser.add_argument(
            "server_names",
            metavar="SERVER_NAME",
            nargs="*",
            help=(
                "Server names to show interfaces for. "
                "If nothing is set, then all server interfaces will be "
                "listed."))

        return parser

    def __init__(self, options):
        super(ListServerInterfaceApp, self).__init__(options)

        self.server_names = sorted(set(options.server_names))
        self.ifname = options.if_name
        self.switch_ip = options.switch_ip
        self.port = options.port
        self.mac_address = options.mac_address
        self.vlan = options.vlan

    def get_info(self):
        session = self.session_maker()

        query = session.query(db.ServerInterface)
        query = query.options(orm.joinedload(db.ServerInterface.server))
        query = query.join(db.Server)

        if self.server_names:
            query = query.filter(db.Server.name.in_(self.server_names))
        if self.ifname:
            query = query.filter(db.ServerInterface.name == self.ifname)
        if self.switch_ip:
            query = query.filter(
                db.ServerInterface.switch_ip == self.switch_ip)
        if self.port:
            query = query.filter(db.ServerInterface.port == self.port)
        if self.mac_address:
            query = query.filter(
                db.ServerInterface.mac_address == self.mac_address)
        if self.vlan:
            query = query.filter(db.ServerInterface.vlan == self.vlan)

        interfaces_data = {}
        for interface in query.all():
            data = interfaces_data.setdefault(interface.server.name, {})
            data[interface.name] = {
                "mac": interface.mac,
                "port": interface.port,
                "vlan": interface.vlan,
                "switch_ip": interface.switch_ip}

        return interfaces_data

    def info_to_csv(self, info):
        for server_name, server_data in sorted(info.iteritems()):
            for if_name, if_data in sorted(server_data.iteritems()):
                yield {
                    "server_name": server_name,
                    "name": if_name,
                    "mac": if_data["mac"],
                    "port": if_data["port"],
                    "vlan": if_data["vlan"],
                    "switch_ip": if_data["switch_ip"]}
