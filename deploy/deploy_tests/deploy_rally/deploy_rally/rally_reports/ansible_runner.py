# coding: utf-8
import os
import sys
from os.path import dirname, abspath, join  # NOQA

from ansible.executor import playbook_executor
from ansible.inventory import Inventory
from ansible.parsing.dataloader import DataLoader
from ansible.utils.display import Display
from ansible.vars import VariableManager

PLAYBOOKS_BASE_DIR = join(dirname(abspath(__file__)), 'playbooks')


class Options(object):
    """Options class to replace Ansible OptParser, In hell it magic"""
    def __init__(self, verbosity=None, inventory=None, listhosts=None,
                 subset=None, module_paths=None, extra_vars=None, forks=None,
                 ask_vault_pass=None, vault_password_files=None,
                 new_vault_password_file=None, output_file=None, tags=None,
                 skip_tags=None, one_line=None, tree=None, ask_sudo_pass=None,
                 ask_su_pass=None, sudo=None, sudo_user=None, become=None,
                 become_method=None, become_user=None, become_ask_pass=None,
                 ask_pass=None, private_key_file=None, remote_user=None,
                 connection=None, timeout=None, ssh_common_args=None,
                 sftp_extra_args=None, scp_extra_args=None,
                 ssh_extra_args=None, poll_interval=None, seconds=None,
                 check=None, syntax=None, diff=None, force_handlers=None,
                 flush_cache=None, listtasks=None, listtags=None,
                 module_path=None, python_interpreter=None):
        self.verbosity = verbosity
        self.inventory = inventory
        self.listhosts = listhosts
        self.subset = subset
        self.module_paths = module_paths
        self.extra_vars = extra_vars
        self.forks = forks
        self.ask_vault_pass = ask_vault_pass
        self.vault_password_files = vault_password_files
        self.new_vault_password_file = new_vault_password_file
        self.output_file = output_file
        self.tags = tags
        self.skip_tags = skip_tags
        self.one_line = one_line
        self.tree = tree
        self.ask_sudo_pass = ask_sudo_pass
        self.ask_su_pass = ask_su_pass
        self.sudo = sudo
        self.sudo_user = sudo_user
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.become_ask_pass = become_ask_pass
        self.ask_pass = ask_pass
        self.private_key_file = private_key_file
        self.remote_user = remote_user
        self.connection = connection
        self.timeout = timeout
        self.ssh_common_args = ssh_common_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.ssh_extra_args = ssh_extra_args
        self.poll_interval = poll_interval
        self.seconds = seconds
        self.check = check
        self.syntax = syntax
        self.diff = diff
        self.force_handlers = force_handlers
        self.flush_cache = flush_cache
        self.listtasks = listtasks
        self.listtags = listtags
        self.module_path = module_path
        self.python_interpreter = python_interpreter


class Runner(object):
    def __init__(self, playbook, hosts='hosts', options=None, passwords=None,
                 vault_pass=None):
        """Init

        :param playbook: str playbook file in playbooks dir
        :param hosts: str path to ansible inventiry file, or hosts list
        :param options: dict options for ansible
            {
                'subset': '~^localhost',
                'become': True,
                'become_method': 'sudo',
                'become_user': 'root',
                'private_key_file': '/path/to/the/id_rsa',
                'tags': 'debug',
                'skip_tags': 'debug',
                'verbosity': 0,
                'remote_user': 'user',
            }
        :param passwords: dict with passwords
            {
                'become_pass': 'password',
            }
        :param vault_pass: str Ansible vault passwords
        """
        if options is None:
            options = {}

        if passwords is None:
            passwords = {}

        # Set options
        self.options = Options()
        for k, v in options.iteritems():
            setattr(self.options, k, v)

        # Gets data from YAML/JSON files
        self.loader = DataLoader()

        # Set display for print message and it verbosity
        self.display = Display(verbosity=self.options.verbosity)

        # Set vault password
        if vault_pass is not None:
            self.loader.set_vault_password(vault_pass)
        elif 'VAULT_PASS' in os.environ:
            self.loader.set_vault_password(os.environ['VAULT_PASS'])

        # All the variables from all the various places
        self.variable_manager = VariableManager()
        if self.options.python_interpreter is not None:
            self.variable_manager.extra_vars = {
                'ansible_python_interpreter': self.options.python_interpreter
            }

        # Set inventory, using most of above objects
        self.inventory = Inventory(
            loader=self.loader, variable_manager=self.variable_manager,
            host_list=hosts)

        if len(self.inventory.list_hosts()) == 0:
            # Empty inventory
            self.display.error("Provided hosts list is empty.")
            sys.exit(1)

        self.inventory.subset(self.options.subset)

        if len(self.inventory.list_hosts()) == 0:
            # Invalid limit
            self.display.error("Specified limit does not match any hosts.")
            sys.exit(1)

        self.variable_manager.set_inventory(self.inventory)

        # Playbook to run.
        playbook = join(PLAYBOOKS_BASE_DIR, playbook)

        # Setup playbook executor, but don't run until run() called
        self.pbex = playbook_executor.PlaybookExecutor(
            playbooks=[playbook],
            inventory=self.inventory,
            variable_manager=self.variable_manager,
            loader=self.loader,
            options=self.options,
            passwords=passwords)

    def run(self):
        # Run Playbook and get stats
        self.pbex.run()
        stats = self.pbex._tqm._stats

        return stats
