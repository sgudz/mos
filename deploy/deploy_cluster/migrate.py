#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Script to migrate switch data to database."""


import argparse
import csv
import os
import sys

import clusterdb as db
import unplugin


ENV_DATA = {
    10: {"capacity": 200},
    11: {"capacity": 50},
    12: {"capacity": 20},
    13: {"capacity": 20},
    14: {"capacity": 10}}

LABSDB_FIELDNAMES = (
    "name",
    "kvm_ip",
    "kvm_pass",
    "eth2_mac",
    "eth3_mac",
    "eth0_mac",
    "wtf",
    "eth2_switch_ip",
    "eth2_port",
    "eth3_switch_ip",
    "eth3_port")

SWITCH = unplugin.DellSwitch()


def main():
    options = get_options()
    session = db.session_factory(options.db_connection)()

    if options.type == "czech":
        server_data = get_server_data(options.labsdb)
        environments = ensure_environments(session)

        switch_db = SWITCH.fill_switches_db()

        for server in server_data:
            ensure_servers(session, switch_db, server, environments)
    elif options.type == "rackspace":
        import_from_rackpsace(session, options.labsdb)
    session.commit()

    return os.EX_OK


def get_server_data(filename):
    with open(filename) as filefp:
        iterator = (line for line in filefp if not line.startswith("#"))
        return list(csv.DictReader(iterator, fieldnames=LABSDB_FIELDNAMES))


def ensure_environments(session):
    environments = {}

    for envnum, envdata in sorted(ENV_DATA.iteritems()):
        env = db.get_or_create(session, db.Environment, name=str(envnum))
        env.vlan = envnum
        env.capacity = envdata["capacity"]
        session.merge(env)
        environments[envnum] = env

    session.commit()

    return environments


def ensure_servers(session, switch_db, labsdb, environments):
    server = db.get_or_create(session, db.Server, name=labsdb["name"])
    server.node_ip = labsdb["kvm_ip"]
    server.node_password = labsdb["kvm_pass"]

    attach_eth0(session, labsdb, server)
    attach_eth2(session, labsdb, switch_db, server)
    attach_eth3(session, labsdb, switch_db, server)

    if server.env_interface and server.env_interface.env_no:
        server.allocated_env = environments[server.env_interface.env_no]
        server.default_env = environments[server.env_interface.env_no]

    session.merge(server)


def attach_eth0(session, labsdb, server):
    eth = db.get_or_create(
        session, db.ServerInterface,
        name="eth0", server=server)
    eth.mac = labsdb["eth0_mac"]

    session.merge(eth)


def attach_eth2(session, labsdb, switchdb, server):
    eth = db.get_or_create(
        session, db.ServerInterface,
        name="eth2", server=server)
    eth.mac = labsdb["eth2_mac"]
    eth.port = labsdb["eth2_port"] or None
    eth.switch_ip = labsdb["eth2_switch_ip"]
    eth.vlan = SWITCH.find_vlan(
        labsdb["eth2_switch_ip"],
        labsdb["eth2_port"],
        switchdb) or None

    session.merge(eth)


def attach_eth3(session, labsdb, switchdb, server):
    eth = db.get_or_create(
        session, db.ServerInterface,
        name="eth3", server=server)
    eth.mac = labsdb["eth3_mac"]
    eth.port = labsdb["eth3_port"] or None
    eth.switch_ip = labsdb["eth3_switch_ip"]
    eth.vlan = SWITCH.find_vlan(
        labsdb["eth3_switch_ip"],
        labsdb["eth3_port"],
        switchdb) or None

    session.merge(eth)


def import_from_rackpsace(db_session, csv_file):
    int_indexes = ["ilo", "em1", "em2", "em3", "em4",
                   "p1p1", "p1p2", "p4p1", "p4p2", "virtual"]
    session = db_session

    with open(csv_file, 'rb') as csvfile:
        csv_line = csv.reader(csvfile, delimiter=',')
        for row in csv_line:
            server = db.get_or_create(session, db.Server, name=row[0])
            server.node_ip = row[0]
            server.node_password = "calvincalvin"
            server.type = "real"
            session.add(server)
            for interface_index in range(1, 10):
                interface = db.get_or_create(
                    session, db.ServerInterface,
                    name=int_indexes[interface_index - 1],
                    mac=row[interface_index],
                    server=server)
                interface.mac = row[interface_index]
                session.add(interface)


def get_options():
    parser = argparse.ArgumentParser(
        description="Migrator of lab data from switches to database.")

    parser.add_argument(
        "-d", "--db-connection",
        help="Connection string to database.",
        default="postgresql://rally:ra11y@1.1.1.1/rally")
    parser.add_argument(
        "-t", "--type",
        choices=['czech', 'rackspace'],
        help="Set csv file type",
        required=True)
    parser.add_argument(
        "labsdb",
        metavar="CSV_FILE",
        help="LabsDB CSV file.")

    return parser.parse_args()


if __name__ == "__main__":
    sys.exit(main())
