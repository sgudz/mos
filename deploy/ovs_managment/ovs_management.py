import argparse
import csv
import ConfigParser
import ipaddr
import libvirt
import os
import sys
import subprocess


from argparse import RawTextHelpFormatter
from prettytable import PrettyTable
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from xml.etree import ElementTree

Base = declarative_base()
MAX_VSWITCH_PORT = 65279


class Server(Base):
    __tablename__ = 'servers'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    interfaces = relationship("Interface", backref="servers")
    type = Column(String)
    env_id = Column(Integer, ForeignKey('environments.id'))


class Interface(Base):
    __tablename__ = 'interfaces'
    id = Column(Integer, primary_key=True)
    server_id = Column(Integer, ForeignKey('servers.id'))
    mac = Column(String, unique=True)
    name = Column(String)


class Environment(Base):
    __tablename__ = 'environments'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    servers = relationship("Server", backref="environments")


class Ovs(object):
    def __init__(self):
        self.libvirt = Libvirt()

    @staticmethod
    def _check_mac(mac):
        mac_length = len(mac.split(":"))
        if mac_length == 6:
            return mac
        else:
            mac += ":00" * (6 - mac_length)
            mac += "/"
            mac += "ff:" * mac_length
            mac = mac[:-1]
            mac += ":00" * (6 - mac_length)
            return mac

    @staticmethod
    def _get_all_vswitches():
        ovs_vsctl_output = subprocess.check_output(["ovs-vsctl", "list-br"])
        return ovs_vsctl_output.split("\n")[:-1]

    def _get_int_id_(self, vm_name):
        vm_list = self.libvirt.get_vm_list()
        if vm_name in vm_list:
            vm_interfaces = self.libvirt.get_interface_index(vm_name)
            all_vswitches = self._get_all_vswitches()
            int_indexes = {}
            for vswitch in all_vswitches:
                ovs_ofctl_out = subprocess.check_output(['ovs-ofctl', 'show',
                                                         vswitch])
                ovs_ofctl_out = ovs_ofctl_out.split("\n")
                for line in ovs_ofctl_out:
                    for vm_interface in vm_interfaces:
                        if line.find(vm_interface) > -1:
                            line = line.strip()
                            i_index, _ = line.split("(")
                            int_indexes[vswitch] = i_index
            return int_indexes
        else:
            return self._get_all_vswitches()

    @staticmethod
    def _deny_mac_access(mac, vswitch):
        print("Deny access for MAC {} in vswitch {}"
              "(interface index is {})".format(mac, vswitch, MAX_VSWITCH_PORT))
        last_arg = ("priority=21,dl_src={},"
                    "actions=output:{}".format(mac, MAX_VSWITCH_PORT))
        subprocess.check_call(["ovs-ofctl", "add-flow", vswitch, last_arg])

    @staticmethod
    def _clean_mac_from_flow(mac, vswitch):
        print("Clean MAC {} from rules in {}".format(mac, vswitch))
        subprocess.check_call(["ovs-ofctl", "del-flows", vswitch,
                               "dl_src={}".format(mac)])

    def _delete_add_mac_in_flow(self, mac, vm_name, operation="delete"):
        mac = self._check_mac(mac)
        vm_interfaces = self._get_int_id_(vm_name)
        if type(vm_interfaces) is dict:
            for key in vm_interfaces:
                self._clean_mac_from_flow(mac, key)
                if operation == "add":
                    print("Add MAC {} in vswitch {} for VM {} "
                          "(interface index is {})".format(mac, key, vm_name,
                                                           vm_interfaces[key]))
                    last_arg = ("priority=21,dl_src={},"
                                "actions=output:{}".format(mac,
                                                           vm_interfaces[key]))
                    subprocess.check_call(["ovs-ofctl", "add-flow", key,
                                           last_arg])
                else:
                    self._deny_mac_access(mac, key)

        else:
            print("WARNING ! Can't modify ovs flows, VM with name {} "
                  "not found".format(vm_name))
            for vswitch in vm_interfaces:
                self._clean_mac_from_flow(mac, vswitch)
                self._deny_mac_access(mac, vswitch)

    def delete_mac_from_flows(self, mac, vm_name):
        self._delete_add_mac_in_flow(mac, vm_name)

    def add_mac_to_flow(self, mac, vm_name):
        self._delete_add_mac_in_flow(mac, vm_name, "add")


class Libvirt(object):
    def __init__(self):
        self.conn = libvirt.openReadOnly(None)
        if self.conn is None:
            print("Failed to open connection to the hypervisor")
            sys.exit(1)

    @staticmethod
    def _get_target_devices(dom):
        tree = ElementTree.fromstring(dom.XMLDesc(0))
        devices = []
        for target in tree.findall("devices/interface/target"):
            dev = target.get("dev")
            if dev not in devices:
                devices.append(dev)
        return devices

    def get_interface_index(self, vm_name):
        vm = self.conn.lookupByName(vm_name)
        interfaces = self._get_target_devices(vm)
        return interfaces

    def get_vm_list(self):
        list_dom = []
        for domain in self.conn.listAllDomains():
            list_dom.append(domain.name())
        return list_dom


class Import(object):
    def __init__(self, db_session):
        self.int_indexes = ["ilo", "em1", "em2", "em3", "em4",
                            "p1p1", "p1p2", "p4p1", "p4p2", "virtual"]
        self.session = db_session

    def import_csv(self, cvs_file):
        with open(cvs_file, 'rb') as csvfile:
            csv_line = csv.reader(csvfile, delimiter=',')
            for row in csv_line:
                interfaces = []
                for interface_index in range(1, 10):
                    interfaces.append(Interface(
                        mac=row[interface_index],
                        name=self.int_indexes[interface_index - 1]))
                n_server = Server(name=row[0],
                                  interfaces=interfaces,
                                  type="hardware")
                self.session.add(n_server)
        self.session.commit()
        print("Import was successful, database updated.")


class Out(object):
    def __init__(self, db_session):
        self.session = db_session
        self.lab_db = LabDatabase(db_session)

    def print_all(self, html_out=False):
        p_table = PrettyTable(["id", "name", "env", "ports"])
        p_table.align = "l"
        p_table.hrules = True
        for l_server in self.session.query(Server):
            interfaces_list = ""
            interfaces = self.lab_db.list_interfaces(l_server.id)
            for interface in interfaces:
                interfaces_list = "{}{} - {}\n".format(interfaces_list,
                                                       interface,
                                                       interfaces[interface])
            interfaces_list = interfaces_list[:-1]
            if l_server.env_id == "" or l_server.env_id is None:
                l_env = ""
            else:
                l_env = self.session.query(Environment).filter(
                    Environment.id == l_server.env_id)[0].name
            p_table.add_row([l_server.id,
                             l_server.name,
                             l_env,
                             interfaces_list])
        if html_out:
            return p_table.get_html_string()
        else:
            print(p_table)

    def print_envs(self, name, html_out=False):
        print("\nThe list of environments\n") if html_out else None
        p_table = PrettyTable(["id", "name", "nodes"])
        p_table.align = "l"
        p_table.hrules = True
        if name == "all":
            envs = self.session.query(Environment)
        else:
            envs = self.session.query(Environment).filter(
                Environment.name == name)
        for env in envs:
            servers_in_env = ""
            count = 1
            if len(env.servers) > 0:
                for env_server in env.servers:
                    servers_in_env = "{}{}, ".format(servers_in_env,
                                                     env_server.name)
                    if count % 4 == 0:
                        servers_in_env = "{}\n".format(servers_in_env)
                    count += 1
            if len(servers_in_env) > 0:
                servers_in_env = servers_in_env[:-2]
            p_table.add_row([env.id, env.name, servers_in_env])
        if html_out:
            return p_table.get_html_string()
        else:
            print(p_table)


class LabDatabase(object):
    def __init__(self, db_session):
        self.session = db_session
        self.ovs = Ovs()

    def list_interfaces(self, server_id):
        interfaces_list = {}
        for interface in self.session.query(Interface).filter(
                Interface.server_id == server_id):
            interfaces_list[interface.name] = interface.mac
        return interfaces_list

    def delete_env_by_id(self, env_id):
        envs = self.session.query(Environment).filter(Environment.id == env_id)
        if envs.count() > 0:
            env_name = self.session.query(Environment).filter(
                Environment.id == env_id)[0].name
            for d_servers in self.session.query(Server).filter_by(
                    env_id=env_id):
                print("Remove server {} from env ".format(
                    d_servers.name, env_name))
                for interface in self.session.query(Interface).filter(
                        Interface.server_id == d_servers.id):
                    self.ovs.delete_mac_from_flows(interface.mac, env_name)
                self.session.query(Server).filter_by(
                    name=d_servers.name).update({"env_id": None})
            self.session.commit()
            print("Delete env {}".format(env_name))
            self.session.query(Environment).filter_by(id=env_id).delete()
            self.session.commit()
        else:
            print("Env with id {} is not found".format(env_id))

    def delete_server_by_name(self, server_name):
        d_server = self.session.query(Server).filter(
            Server.name == server_name)
        if d_server.count() > 0:
            print("Delete server {}".format(server_name))

            env_id = d_server[0].env_id
            if env_id is not None:
                env_name = self.session.query(Environment).filter_by(
                    id=env_id)[0].name
                for interface in self.session.query(Interface).filter(
                        Interface.server_id == d_server[0].id):
                    self.ovs.delete_mac_from_flows(interface.mac, env_name)
            self.session.query(Interface).filter_by(
                server_id=d_server[0].id).delete()
            self.session.query(Server).filter_by(name=server_name).delete()
            self.session.commit()
        else:
            print("Server {} is not found".format(server_name))

    def check_and_create_env(self, name):
        if name == "":
            print("The empty name for environment is bad idea")
            sys.exit(1)
        env_in_db = (self.session.query(Environment.id).filter(
            Environment.name == name))
        if env_in_db.count() == 0:
            print("Environment {} is unknown, creating new env".format(name))
            n_env = Environment(name=name)
            self.session.add(n_env)
            self.session.commit()
        else:
            print("Environment {} already exist".format(name))

    def check_and_create_server(self, name, interfaces=None):
        if self.session.query(Server).filter(Server.name == name).count() == 0:
            print("Server {} is not found, adding".format(name))
            if name.find(":") > 0:
                interfaces = Interface(mac=name, name="virt")
            if interfaces is None:
                print("WARNING ! You are creating server without interfaces, "
                      "don't forget to add the interfaces")
                n_server = Server(name=name,
                                  type="hardware")
            else:
                print("Adding interface {} - {} to server {}".format(
                    interfaces.name, interfaces.mac, name
                ))
                n_server = Server(name=name,
                                  interfaces=[interfaces],
                                  type="hardware")
            self.session.add(n_server)
            self.session.commit()
        else:
            print("Server {} already exist".format(name))

    def assign_server_to_env_by_id(self, server_id, env_id):
        server_name = self.session.query(Server).filter_by(
            id=server_id)[0].name
        env_name = self.session.query(Environment).filter_by(
            id=env_id)[0].name
        self.assign_server_to_env(server_name, env_name)

    def remove_server_from_env_by_id(self, server_id):
        env_id = self.session.query(Server).filter_by(
            id=server_id)[0].env_id
        env_name = self.session.query(Environment).filter_by(
            id=env_id)[0].name
        if env_id is not None:
            for interface in self.session.query(Interface).filter(
                    Interface.server_id == server_id):
                self.ovs.delete_mac_from_flows(interface.mac, env_name)
            self.session.query(Server).filter_by(
                id=server_id).update({"env_id": None})
            self.session.commit()

    def assign_server_to_env(self, server_name, env_name):
        if self.session.query(Server).filter(
                Server.name == server_name).count() == 0:
            self.check_and_create_server(server_name)
        else:
            print("Adding {} to env {}".format(server_name, env_name))
            self.session.query(Server).filter_by(name=server_name).update(
                {"env_id": self.session.query(Environment.id).filter(
                    Environment.name == env_name)[0].id})
            server = self.session.query(Server).filter(
                Server.name == server_name)[0]
            for interface in self.session.query(Interface).filter(
                    Interface.server_id == server.id):
                self.ovs.add_mac_to_flow(interface.mac, env_name)

    def add_interface_to_server(self, int_name, int_mac, server_name):
        if self.session.query(Server).filter(
                Server.name == server_name).count() == 0:
            interfaces = Interface(mac=int_mac, name=int_name)
            self.check_and_create_server(server_name, interfaces)
        else:
            if self.session.query(Interface).filter(
                    Interface.mac == int_mac).count() == 0:
                print("Adding interface {} - {} to server {}".format(
                    int_name, int_mac, server_name
                ))
                server_id = self.session.query(Server).filter(
                    Server.name == server_name)[0].id
                new_interface = Interface(mac=int_mac,
                                          name=int_name,
                                          server_id=server_id)
                self.session.add(new_interface)
                self.session.commit()
            if self.session.query(Server).filter(
                    Server.name == server_name)[0].env_id is not None:
                env_id = self.session.query(Server).filter(
                    Server.name == server_name)[0].env_id
                env_name = self.session.query(Environment).filter_by(
                    id=env_id)[0].name
                self.ovs.add_mac_to_flow(int_mac, env_name)
            else:
                print("Can't add this interface this MAC already added")

    def delete_interface(self, int_mac):
        mac_query = self.session.query(Interface).filter(
            Interface.mac == int_mac)
        if mac_query.count() > 0:
            print("Deleting interface")
            env_id = self.session.query(Server).filter_by(
                id=mac_query[0].server_id)[0].env_id
            env_name = self.session.query(Environment).filter_by(
                id=env_id)[0].name
            self.ovs.delete_mac_from_flows(mac_query[0].mac, env_name)
            self.session.query(Interface).filter_by(mac=int_mac).delete()
            self.session.commit()
        else:
            print("Can't find this interface in database")

    def list_all_servers(self):
        return self.list_servers_in_env("all")

    def list_servers_in_env(self, env_id="all"):
        list_servers = {}
        if env_id == "all":
            servers = self.session.query(Server)
        elif env_id == "none":
            servers = self.session.query(Server).filter_by(env_id=None)
        else:
            servers = self.session.query(Server).filter_by(env_id=env_id)
        for server in servers:
            list_servers[server.id] = [server.name]
            if server.env_id == "" or server.env_id is None:
                list_servers[server.id].append("")
            else:
                list_servers[server.id].append(self.session.query(
                    Environment).filter_by(id=server.env_id)[0].name)
            interfaces_list = self.list_interfaces(server.id)
            list_servers[server.id].append(interfaces_list)
        return list_servers

    def list_all_env(self):
        list_envs = {}
        for env in self.session.query(Environment):
            list_envs[env.name] = env.id
        return list_envs


class Main(object):
    def __init__(self):
        if not os.geteuid() == 0:
            print("This script working only from user root")
            sys.exit(1)
        parser = self.create_parser()
        self.parsed = parser.parse_args()
        if self.parsed.db_connection is not None:
            db_url = self.parsed.db_connection
        else:
            config = ConfigParser.RawConfigParser()
            config.read('ovs_management.cfg')
            db_url = config.get('db', 'db_url')
        if db_url.find('sqlite') == 0:
            _, db_path = db_url.split('///')
            if not os.path.isdir(os.path.dirname(db_path)):
                print("Can't find db path {}, creating".format(
                    os.path.dirname(db_path)))
                os.mkdir(os.path.dirname(db_path))
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        session = sessionmaker(bind=self.engine)
        self.session = session()
        self.out = Out(self.session)
        self.lab_db = LabDatabase(self.session)
        self.import_csv = Import(self.session)

    @staticmethod
    def create_parser():
        l_parser = argparse.ArgumentParser(
            description=(
                "This is a script to manage access to DHCP for servers in "
                "rackspace/intel lab. "
                "Please check subcommand help for details."),
            formatter_class=RawTextHelpFormatter
        )
        l_group = l_parser.add_mutually_exclusive_group()
        l_group.add_argument(
            "-a", "--all",
            help="Print all records in database",
            action="store_true",
            default=False)
        l_group.add_argument(
            "-f", "--file-import",
            dest="fileimport",
            help="Import csv file to database.",
            default=False)
        l_group.add_argument(
            "--add-env",
            dest="add_env",
            metavar="ENV-NAME",
            help="Add environment (use VM name as environment) "
        )
        l_group.add_argument(
            "--add-int",
            dest="add_int",
            nargs=3,
            metavar=("INT-NAME", "INT-MAC", "SERVER-NAME"),
            help="Add interface to server"
        )
        l_group.add_argument(
            "--delete-int",
            dest="del_int",
            metavar="INT-MAC",
            help="Delete interface from database"
        )
        l_group.add_argument(
            "--print-env",
            dest="print_env",
            help="Print list of environments. all for all environments"
        )
        l_group.add_argument(
            "--delete-env",
            dest="delete_env",
            metavar="ENV-ID",
            help="Delete environments"
        )
        l_group.add_argument(
            "--delete-server",
            dest="delete_server",
            metavar="SERVER-NAME",
            help="Delete server"
        )
        l_group.add_argument(
            "--add-servers-to-env",
            nargs=2,
            dest="add_servers_to_env",
            metavar=("SERVERS", "ENV-NAME"),
            help="Add servers to env.\nExamples:\n"
                 "--add-servers-to-env 10.20.1.2 vm-name (add single server)\n"
                 "--add-servers-to-env 10.20.1.2-10.20.1.20 vm-name "
                 "(add range of servers)\n"
                 "--add-servers-to-env 52:54 vm-name (add prefix for VMs)\n"

        )
        l_parser.add_argument(
            "-c", "--db-connection",
            dest="db_connection",
            help="Database connection string for SQLAlchemy.\n"
                 "If not set, get from ovs_management.cfg")

        if len(sys.argv) == 1:
            l_parser.print_help()
            sys.exit(1)
        return l_parser

    @staticmethod
    def generate_ip_range(start, end):
        servers_range = []
        ip = start
        while ip <= end:
            servers_range.append(str(ip))
            ip += 1
        return servers_range

    def assign_servers_to_env(self, servers, env):
        self.lab_db.check_and_create_env(env)
        if servers.find("-") > 0:
            # Range of IPs
            ip_range = servers.split("-")
            servers_list = self.generate_ip_range(
                ipaddr.IPAddress(ip_range[0]),
                ipaddr.IPAddress(ip_range[1]))
            for server in servers_list:
                self.lab_db.check_and_create_server(server)
                self.lab_db.assign_server_to_env(server, env)
            self.session.commit()
        elif servers.find(":") > 0:
            # MACs of VMs
            self.lab_db.check_and_create_server(servers)
            self.session.commit()
            self.lab_db.assign_server_to_env(servers, env)
            self.session.commit()
        else:
            # Single IP
            self.lab_db.check_and_create_server(servers)
            self.lab_db.assign_server_to_env(servers, env)
            self.session.commit()

    def main(self):
        if self.parsed.fileimport:
            self.import_csv.import_csv(self.parsed.fileimport)
        if self.parsed.all:
            self.out.print_all()
        if self.parsed.add_env:
            self.lab_db.check_and_create_env(self.parsed.add_env)
        if self.parsed.add_int:
            self.lab_db.add_interface_to_server(
                self.parsed.add_int[0],
                self.parsed.add_int[1],
                self.parsed.add_int[2])
        if self.parsed.del_int:
            self.lab_db.delete_interface(self.parsed.del_int)
        if self.parsed.print_env:
            self.out.print_envs(self.parsed.print_env)
        if self.parsed.add_servers_to_env:
            self.assign_servers_to_env(
                self.parsed.add_servers_to_env[0],
                self.parsed.add_servers_to_env[1])

        if self.parsed.delete_env:
            self.lab_db.delete_env_by_id(self.parsed.delete_env)
        if self.parsed.delete_server:
            self.lab_db.delete_server_by_name(self.parsed.delete_server)


if __name__ == "__main__":
    main = Main()
    sys.exit(main.main())
