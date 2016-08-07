# -*- coding: utf-8 -*-
"""
Common database routines for scale lab DB.
"""

import logging

import sqlalchemy as sq
import sqlalchemy.ext.declarative
import sqlalchemy.orm as orm

from base_nodes_info_driver import BaseNodesInfoDriver

IPV4_LENGTH = len("255.255.255.255")
"""Length of IPv4 address."""

MAC_LENGTH = len("xx:xx:xx:xx:xx:xx")
"""Length of MAC address."""

MEANINGFUL_PASSWORD_LENGTH = 32
"""Password length (max)."""

MEANINGFUL_PORT_LENGTH = len("99/999")
"""Maximal port definition length."""

Base = sqlalchemy.ext.declarative.declarative_base()
"""Table base."""

WAIT_SERVERS_DELAY = 5  # seconds
"""How long to wait before polling on server status on IPMI."""

WAIT_SERVERS_TIMEOUT = 60 * 15  # seconds
"""How long to wait for server to change its state."""

LOG = logging.getLogger(__name__)
"""Logger."""


class Environment(Base):
    __tablename__ = "environments"

    _id = sq.Column(
        sq.Integer,
        primary_key=True)
    name = sq.Column(sq.String, unique=True, nullable=False)
    capacity = sq.Column(
        sq.Integer, sq.CheckConstraint("capacity > 0"),
        nullable=False)
    type = sq.Column(sq.String, unique=False, nullable=True)
    param = sq.Column(sq.String, unique=False, nullable=True)


class Server(Base):
    __tablename__ = "servers"

    _id = sq.Column(
        sq.Integer,
        primary_key=True)
    name = sq.Column(
        sq.String,
        unique=True)
    type = sq.Column(
        sq.String,
        unique=False)
    default_env_id = sq.Column(
        sq.Integer, sq.ForeignKey(Environment._id, ondelete="SET NULL"))
    allocated_env_id = sq.Column(
        sq.Integer, sq.ForeignKey(Environment._id, ondelete="SET NULL"))
    node_ip = sq.Column(
        sq.String(IPV4_LENGTH),
        unique=False, nullable=False)
    node_password = sq.Column(
        sq.String(MEANINGFUL_PASSWORD_LENGTH),
        nullable=False)

    default_env = orm.relationship(
        Environment,
        foreign_keys=default_env_id,
        backref=orm.backref("default_servers", order_by=_id))
    allocated_env = orm.relationship(
        Environment,
        foreign_keys=allocated_env_id,
        backref=orm.backref("allocated_servers", order_by=_id))

    @property
    def interface_map(self):
        return {interface.name: interface for interface in self.interfaces}


class ServerInterface(Base):
    __tablename__ = "server_interfaces"

    _id = sq.Column(
        sq.Integer,
        primary_key=True)
    name = sq.Column(
        sq.String,
        nullable=False)
    mac = sq.Column(
        sq.String(MAC_LENGTH),
        nullable=False, unique=True)
    port = sq.Column(
        sq.String(MEANINGFUL_PORT_LENGTH),  # because of weird 1/17 etc
        nullable=True, default=None)
    vlan = sq.Column(
        sq.Integer, sq.CheckConstraint("0 < vlan AND vlan <= 4096"),
        nullable=True, default=None)
    switch_ip = sq.Column(
        sq.String(IPV4_LENGTH),
        nullable=True, default=None)
    server_id = sq.Column(
        sq.Integer, sq.ForeignKey(Server._id, ondelete="CASCADE"))

    server = orm.relationship(
        Server,
        backref=orm.backref("interfaces", order_by=name))

    __table_args__ = (
        sq.UniqueConstraint(mac, vlan),
        sq.UniqueConstraint(mac, port),
        sq.UniqueConstraint(mac, switch_ip),
        sq.UniqueConstraint(server_id, name),
        {})


class DatabaseDriver(BaseNodesInfoDriver):
    def __init__(self, connection_string):
        engine = sq.create_engine(connection_string)
        Base.metadata.create_all(engine)

        self.session_maker = orm.sessionmaker(bind=engine,
                                              autocommit=False,
                                              autoflush=False)

    def get_env_info(self, env_name):
        env_info = {}
        session = self.session_maker()
        env_obj = session.query(Environment). \
            filter(Environment.name == env_name).first()
        if env_obj:
            env_info["name"] = env_obj.name
            env_info["capacity"] = env_obj.capacity
            env_info["ovs_driver"] = env_obj.type
            env_info["vm_pxe_server_name"] = env_obj.param

        return env_info

    def assign_nodes_to_env(self, nodes, env_name):
        LOG.info("Allocate {} servers to {} environment".format(
                 ",".join(nodes.keys()), env_name))
        session = self.session_maker()
        if env_name:
            env = session.query(Environment).filter(
                Environment.name == env_name).first()
            env_id = env._id
        else:
            env_id = None
        server_list = session.query(Server).\
            filter(Server.name.in_(nodes.keys())).all()
        if len(server_list) != len(nodes):
            raise Exception
        for srv_obj in server_list:
            srv_obj.allocated_env_id = env_id
            session.merge(srv_obj)
        session.commit()

        return True

    def get_nodes_by_env(self, env_name):
        nodes = {}
        session = self.session_maker()
        env = session.query(Environment).filter(
            Environment.name == env_name).first()
        servers = session.query(Server).filter(
            Server.default_env_id == env._id).all()
        for server in servers:
            nodes[server.name] = {}
            node = nodes[server.name]
            node["name"] = server.name
            node["ip"] = server.node_ip
            node["password"] = server.node_password
            node["power_driver"] = server.type
            node["default_env"] = server.default_env_id
            node["allocated_env"] = server.allocated_env_id
            node["interfaces"] = {}
            for inter in server.interface_map:
                node["interfaces"][inter] = {
                    "mac": server.interface_map[inter].mac,
                    "switch_ip": server.interface_map[inter].switch_ip,
                    "port": server.interface_map[inter].port}
        return nodes
