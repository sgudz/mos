import logging
import os
import subprocess

from base_power_driver import BasePowerDriver


class SuperMicroIPMIDriver(BasePowerDriver):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)
        self.ipmi_path = ['bin', 'sbin']
        self.ipmi = None
        for path in self.ipmi_path:
            if os.path.exists('/usr/{0}/ipmitool'.format(path)):
                self.ipmi = '/usr/{0}/ipmitool'.format(path)
                break
        if not self.ipmi:
            raise RuntimeError('power_manager not found')

    def power_status(self, ip, name, username, password):
        out = self._exec_ipmi(ip, username, password, 'power status')
        if out.find('Chassis Power is on') == 0:
                return True
        elif out.find('Chassis Power is off') == 0:
                return False
        return None

    def power_off(self, ip, name, username, password):
        self.logger.debug("Try to power off node by SuperMicroIPMI plugin")
        out = self._exec_ipmi(ip, username, password, 'power off')
        if out.find('Chassis Power Control: Down/Off') != 0:
            self.logger.warning('Can\'t power off node. Output is {0}'.
                                format(out))
            return None
        return True

    def power_on(self, ip, name, username, password):
        self.logger.debug("Try to power on node by SuperMicroIPMI plugin")
        out = self._exec_ipmi(ip, username, password, 'power on')
        if out.find('Chassis Power Control: Up/On') != 0:
            self.logger.warning('Can\'t power on node. Output is {0}'.
                                format(out))
            return None
        return True

    def _exec_ipmi(self, ip, username, password, command):
        ipmi_cmd = [self.ipmi,
                    '-H', ip,
                    '-I', 'lanplus',
                    '-U', username,
                    '-P', password]
        cmd1, cmd2 = command.split()
        command = [cmd1, cmd2]
        cmd = ipmi_cmd + command
        output = subprocess.check_output(cmd)
        output = output.strip()
        self.logger.debug(cmd)
        self.logger.debug('IPMI output is "{0}"'.format(output))
        return output
