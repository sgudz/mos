from unittest import TestCase
from mock import patch

from deploy.deploy_cluster.plugins.power_manager.drivers.\
    supermicro_ipmi_driver import SuperMicroIPMIDriver


class TestSuperMicroIPMIDriver(TestCase):
    @patch("deploy.deploy_cluster.plugins.power_manager."
           "drivers.supermicro_ipmi_driver.SuperMicroIPMIDriver._exec_ipmi")
    def test_power_status(self, mock__exec_ipmi):
        mock__exec_ipmi.return_value = "Chassis Power is on"
        ipmi = SuperMicroIPMIDriver()
        self.assertEqual(ipmi.power_status("1.1.1.1", "node-node",
                                           "username", "password"), True)

        mock__exec_ipmi.return_value = "Chassis Power is off"
        self.assertEqual(ipmi.power_status("1.1.1.1", "node-node",
                                           "username", "password"), False)

        mock__exec_ipmi.return_value = "Something wrong"
        self.assertEqual(ipmi.power_status("1.1.1.1", "node-node",
                                           "username", "password"), None)

    @patch("deploy.deploy_cluster.plugins.power_manager."
           "drivers.supermicro_ipmi_driver.SuperMicroIPMIDriver._exec_ipmi")
    def test_power_off(self, mock__exec_ipmi):
        mock__exec_ipmi.return_value = "Chassis Power Control: Down/Off"
        ipmi = SuperMicroIPMIDriver()
        self.assertEqual(ipmi.power_off("1.1.1.1", "node-node",
                                        "username", "password"), True)
        mock__exec_ipmi.return_value = "Something wrong"
        self.assertEqual(ipmi.power_off("1.1.1.1", "node-node",
                                        "username", "password"), None)

    @patch("deploy.deploy_cluster.plugins.power_manager."
           "drivers.supermicro_ipmi_driver.SuperMicroIPMIDriver._exec_ipmi")
    def test_power_on(self, mock__exec_ipmi):
        mock__exec_ipmi.return_value = "Chassis Power Control: Up/On"
        ipmi = SuperMicroIPMIDriver()
        self.assertEqual(ipmi.power_on("1.1.1.1", "node-node",
                                       "username", "password"), True)
        mock__exec_ipmi.return_value = "Something wrong"
        self.assertEqual(ipmi.power_on("1.1.1.1", "node-node",
                                       "username", "password"), None)
