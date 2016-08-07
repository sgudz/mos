# coding: utf-8
from __future__ import absolute_import

import os
from tempfile import NamedTemporaryFile

import ansible.constants
from tabulate import tabulate

from .ansible_runner import Runner  # NOQA
from .base import TemplateJinjaReport  # NOQA
from .utils import parse_astute  # NOQA

ansible.constants.HOST_KEY_CHECKING = False


class BaseRstReport(TemplateJinjaReport):
    """Class for RST report

    !!! Do not add anything here that is not necessary in all classes
        descendants. If you need additional fuctionality for a particular class
        redefine methods.
    """
    # This is the matching of OpenStack components and rally atomic actions.
    # Should be defined in each cild of BaseRstReport class.
    ACTION_TO_SERVICE_MAP = {}

    # default query, fetch min,median,max and group by every field.
    query = (
        "SELECT mean(value), percentile(value, 90) as perc90, "
        "percentile(value, 50) as perc50, min(value),median(value),max(value) "
        "FROM rally "
        "WHERE jenkins_build_number='{deployment}' "
        "GROUP BY * fill(none)"
    )

    def __init__(self, db, options):
        super(BaseRstReport, self).__init__(db, options)
        self.roles = parse_astute(options.astute_yaml)
        self.playbook = 'collect_files.yaml'
        self.private_key_file = '/root/.ssh/id_rsa'

    def serialize_data(self):
        """Serialize ResultSet and adapt to our needs.

        :return:
        """
        res = super(BaseRstReport, self).serialize_data()
        data = {}

        for el in res:
            if el['status'] == 'failed':
                continue

            atomic_name = el['atomic_name']
            if atomic_name not in self.ACTION_TO_SERVICE_MAP:
                continue
            service_name = self.ACTION_TO_SERVICE_MAP[atomic_name]

            if service_name not in data:
                data[service_name] = {"actions": [], "table": ""}
            data[service_name]["actions"].append([
                atomic_name.split(".")[1],
                el['mean'],
                el['perc90'],
                el['perc50'],
                el['max'],
                el['min']
            ])

        headers = ["Operation", "Mean", "90%ile", "50%ile", "Max", "Min"]
        for service_name in data:
            service = data[service_name]
            service["table"] = tabulate(service["actions"],
                                        headers=headers,
                                        tablefmt="grid")

        return {"data": data, "roles": self.roles}

    def collect_additional_files(self):
        """Collect etc files and OS configuration from fuel nodes

        :return:
        """
        inventory = self._generate_inventory()

        options = {
            'private_key_file': self.private_key_file,
            'become': True,
            'verbosity': 100,
            'connection': 'smart',
            'become_method': 'sudo',
            'become_user': 'root',
            'remote_user': 'root',
            'skip_tags': 'debug',
        }

        r = Runner(playbook=self.playbook, hosts=inventory, options=options)
        r.run()

        # clean temp inventory file
        os.remove(inventory)

    def generate_report(self):
        """Run rst file generation and collection files.

        :return:
        """
        self.save_as_file(self.options.rst_file)
        self.collect_additional_files()

    def _generate_inventory(self):
        """Calculate hosts for ansible inventory from fuel roles.

        Create temp inventory file which need remove after usage!

        :return: list
        """
        inventiry_file = NamedTemporaryFile(delete=False)

        inventiry_file.write("[hosts]\n")

        for role_name, role in self.roles.iteritems():
            for index, node in enumerate(role["nodes"], start=1):
                inventiry_file.write("{}-{}\tansible_host={}\n".format(
                    role_name, index, node['ip']))

                # only one compute node
                if role_name != "controller":
                    break

        return inventiry_file.name


class PerformanceRstReport(BaseRstReport):
    ACTION_TO_SERVICE_MAP = {
        "nova.boot_server": "Nova",
        "cinder.create_volume": "Cinder",
        "nova.attach_volume": "Nova",
        "nova.find_host_to_migrate": "Nova",
        "nova.live_migrate": "Nova",
        "nova.detach_volume": "Nova",
        "nova.delete_server": "Nova",
        "cinder.delete_volume": "Cinder",
        "glance.create_image": "Glance",
        "glance.delete_image": "Glance",
        "authenticate.keystone": "Keystone",
        "nova.create_2_security_groups": "Neutron",
        "nova.create_20_rules": "Neutron",
        "nova.delete_2_security_groups": "Neutron"
    }

    template = "performance_report.rst"


class DensityRstReport(BaseRstReport):
    ACTION_TO_SERVICE_MAP = {
        "nova.boot_server": "Nova",
        "cinder.create_volume": "Cinder",
        "nova.attach_volume": "Nova",
        "nova.create_10_security_groups": "Neutron",
        "nova.create_100_rules": "Neutron",
        "nova.list_security_groups": "Neutron",
        "nova.list_servers": "Nova"
    }

    template = "density_report.rst"


RST_REPORT_FABRIC = {
    "performance": PerformanceRstReport,
    "density": DensityRstReport
}
