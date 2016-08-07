#    Copyright 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
# conf t
# int vlan 10
# no untagged TenGigabitEthernet 0/43
# untagged TenGigabitEthernet 0/44

import logging
import pexpect
import sys
import time

from base_switch_driver import BaseSwitchDriver


class DellSwitchDriver(BaseSwitchDriver):
    def __init__(self):
        self.ssh_cmd = ('ssh -o StrictHostKeyChecking=no '
                        '-o UserKnownHostsFile=/dev/null ')
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

    def remove_ports_from_vlan(self, switch_ip, switch_username,
                               switch_password, vlan, ports):
        self.logger.debug('\n========= Start remove ports from vlan '
                          '==============')
        all_ports = ','.join(map(str, ports))
        cmd = ['interface vlan {0}'.format(vlan),
               'no untagged TenGigabitEthernet 0/{0}'.format(all_ports)]
        self._cmd_execute(switch_ip, switch_username, switch_password,
                          cmd, config=True)
        self.logger.debug('\n========== Stop remove ports from vlan '
                          '==============')
        return True

    def add_ports_to_vlan(self, switch_ip, switch_username,
                          switch_password, vlan, ports):
        self.logger.debug('\n========= Start add ports to vlan ==============')
        all_ports = ','.join(map(str, ports))
        cmd = ['interface vlan {0}'.format(vlan),
               'untagged TenGigabitEthernet 0/{0}'.format(all_ports)]
        self._cmd_execute(switch_ip, switch_username, switch_password,
                          cmd, config=True)
        self.logger.debug('\n========== Stop add ports to vlan ==============')
        return True

    def _cmd_execute(self, ip, username, password, cmds, config=False,
                     sleep=0):
        prompt = '#'
        self.logger.debug('Try to execute {0} on {1}'.format(cmds, ip))
        output = ''
        try:
            ssh = pexpect.spawn("{} {}@{}".format(self.ssh_cmd, username, ip),
                                maxread=1, timeout=300)
            ssh.timeout = 300
            self.logger.debug('\n************** SSH output *****************')
            ssh.logfile = sys.stdout
            ssh.expect('password:')
            time.sleep(0.5)
            ssh.sendline(password)
            ssh.expect(prompt)
            ssh.sendline('terminal length 0')
            ssh.expect(prompt)
            if config:
                ssh.sendline('configure terminal')
                ssh.expect(prompt)
            for cmd in cmds:
                ssh.sendline(cmd)
                ssh.expect(prompt)
                output = output + ssh.before
            if config:
                for count in range(0, len(cmds)):
                        ssh.sendline('exit')
                        ssh.expect(prompt)
            ssh.sendline('exit')
            ssh.close()
        except pexpect.EOF as e:
            sleep += 5
            self.logger.debug(
                'Ssh die with error \n'
                'EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE\n'
                '{}\n'
                '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n'
                'try again after {} seconds'.
                format(e, sleep))
            if sleep > 30:
                raise RuntimeError("Can't work with switch")
            time.sleep(sleep)
            self._cmd_execute(ip, cmds, config, sleep)
        self.logger.debug('\n***************************************')
        return output
