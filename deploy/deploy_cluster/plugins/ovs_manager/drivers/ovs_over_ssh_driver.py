import logging
import re
from tempfile import NamedTemporaryFile
from paramiko import SSHClient
from paramiko import AutoAddPolicy
from scp import SCPClient

from base_ovs_driver import BaseOVSDriver


class OVSOverSSHDriver(BaseOVSDriver):
    def __init__(self, ovs_servers):
        logging.basicConfig(level=logging.DEBUG)
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.logger = logging.getLogger(__name__)

        self.ovs_info = self._get_info_from_ovs_servers(ovs_servers)

    def add_block_rules_for_macs(self, mac_list):
        for ovs_server, ovs_info in self.ovs_info.iteritems():
            self.logger.debug("Getting info from '{}'".format(ovs_server))
            bridges_info = ovs_info["bridges_info"]
            cred = {"username": ovs_info["username"],
                    "password": ovs_info["password"]}
            for bridge in bridges_info:
                flow_list = []
                for mac in mac_list:
                    flow_list.append("dl_src={},actions=drop".format(mac))
                with NamedTemporaryFile() as tmp_file:
                    tmp_file.write("\n".join(flow_list))
                    tmp_file.flush()
                    self._scp_command(ovs_server,
                                      cred["username"],
                                      cred["password"],
                                      tmp_file.name,
                                      tmp_file.name)
                    cmd = "ovs-ofctl mod-flows {} - < {}".format(
                        bridge, tmp_file.name)
                    self._remote_command(ovs_server, cred["username"],
                                         cred["password"], cmd)
                    cmd = "find {0} -path {0} -delete".format(tmp_file.name)
                    self._remote_command(ovs_server, cred["username"],
                                         cred["password"], cmd)
        return

    def add_permit_rules_for_macs(self, mac_list, vm_pxe_server_name):
        self.logger.debug("Add permit rule for {}".format(mac_list))
        vm_ports_info = None

        for ovs_server, ovs_info in self.ovs_info.iteritems():
            cred = {"username": ovs_info["username"],
                    "password": ovs_info["password"]}
            bridges_info = ovs_info["bridges_info"]
            vm_list = ovs_info["vm_list"]
            if vm_pxe_server_name in vm_list:
                vm_ports = self._get_vm_ports(ovs_server, cred,
                                              vm_pxe_server_name)
                vm_ports_info = self._generate_vm_ports_info(bridges_info,
                                                             vm_ports)
                target_ovs_server = ovs_server
                break

        if not vm_ports_info:
            raise Exception("Can't find env pxe server {}".format(
                vm_pxe_server_name))

        for bridge_name, port_list in vm_ports_info.iteritems():
            flow_list = []
            for mac in mac_list:
                flow_list.append("dl_src={},actions={}".format(
                    mac, ",".join(port_list)))
            with NamedTemporaryFile() as tmp_file:
                tmp_file.write("\n".join(flow_list))
                tmp_file.flush()
                self._scp_command(target_ovs_server,
                                  cred["username"],
                                  cred["password"],
                                  tmp_file.name,
                                  tmp_file.name)
                cmd = "ovs-ofctl mod-flows {} - < {}".format(
                    bridge_name, tmp_file.name)
                self._remote_command(target_ovs_server, cred["username"],
                                     cred["password"], cmd)
                cmd = "find {0} -path {0} -delete".format(tmp_file.name)
                self._remote_command(target_ovs_server, cred["username"],
                                     cred["password"], cmd)
        return

    def _get_info_from_ovs_servers(self, ovs_servers):
        ovs_info = {}
        for ovs_server, cred in ovs_servers.iteritems():
            bridge_list = self._get_bridge_list(ovs_server, cred)
            bridges_info = {}
            for bridge_name in bridge_list:
                bridge_ports = self._get_bridge_ports(ovs_server, cred,
                                                      bridge_name)

                bridges_info[bridge_name] = bridge_ports

            vm_list = self._get_vm_list(ovs_server, cred)

            ovs_info[ovs_server] = {"username": cred["username"],
                                    "password": cred["password"],
                                    "bridges_info": bridges_info,
                                    "vm_list": vm_list}

        return ovs_info

    def _generate_vm_ports_info(self, bridges_info, vm_ports):
        vm_ports_info = {}
        found_ports = 0
        for bridge_name, bridge_ports in bridges_info.iteritems():
            for bridge_port in bridge_ports:
                if bridge_port["name"] in vm_ports:
                    if bridge_name not in vm_ports_info:
                        vm_ports_info[bridge_name] = []
                    vm_ports_info[bridge_name]. \
                        append(bridge_port["id"])
                    found_ports += 1
                    if found_ports >= len(vm_ports):
                        break
            if found_ports >= len(vm_ports):
                break

        return vm_ports_info

    def _get_vm_list(self, ovs_server, cred):
        cmd = "virsh list"
        output = self._remote_command(ovs_server, cred["username"],
                                      cred["password"], cmd)
        vm_list = \
            [br_name.strip().split()[1] for
             br_name in output.split('\n')[2:] if br_name]
        return vm_list

    def _get_vm_ports(self, ovs_server, cred, vm_name):
        cmd = ("virsh domiflist {}".format(vm_name))
        output = self._remote_command(ovs_server, cred["username"],
                                      cred["password"], cmd)
        vm_ports = [port.strip().split()[0] for
                    port in output.split("\n")[2:] if port]
        return vm_ports

    def _get_bridge_list(self, ovs_server, cred):
        cmd = "ovs-vsctl list-br"
        output = self._remote_command(ovs_server, cred["username"],
                                      cred["password"], cmd)
        bridges_list = [br_name for br_name in output.split('\n') if br_name]
        return bridges_list

    def _get_bridge_ports(self, ovs_server, cred, bridge_name):
        cmd = "ovs-ofctl show {}".format(bridge_name)
        output = self._remote_command(ovs_server, cred["username"],
                                      cred["password"], cmd)
        ports_info = re.findall("(\d+)\((vnet\d+)\):", output)
        ports = []
        for port_info in ports_info:
            ports.append({"id": port_info[0],
                          "name": port_info[1]})
        return ports

    def _remote_command(self, server, username, password, remote_command):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        self.logger.debug("Execute '{}' on server {}".format(
            remote_command, server))

        ssh.connect(hostname=server, username=username,
                    password=password)

        stdin, stdout, stderr = ssh.exec_command(remote_command)
        out = [stdout.read().strip(), stderr.read().strip()]
        if out[0]:
            self.logger.debug("Output is '{}'".format(out[0]))
        if out[1]:
            self.logger.warning("Error is {}".format(out[1]))
        ssh.close()
        return out[0]

    def _scp_command(self, server, username, password,
                     local_file, remote_file):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())

        ssh.connect(hostname=server, username=username,
                    password=password)

        scp = SCPClient(ssh.get_transport())

        scp.put(local_file, remote_file)

        scp.close()
