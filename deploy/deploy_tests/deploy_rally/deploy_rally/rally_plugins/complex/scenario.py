
import imp
import os

from rally.common import objects
from rally import osclients
from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.cinder import utils as cinder_utils
from rally.plugins.openstack.scenarios.keystone import utils as key_utils
from rally.plugins.openstack.scenarios.neutron import utils as net_utils
from rally.plugins.openstack.scenarios.nova import utils as nova_utils
from rally.task import types
from rally.task import validation


consts = imp.load_source(
    "consts",
    os.path.join(os.path.abspath(__file__).rsplit("/", 1)[0], "consts.py"))


class NovaAndNeutronHelper(nova_utils.NovaScenario,
                           net_utils.NeutronScenario,
                           cinder_utils.CinderScenario):

    def create_network_with_subnet(self, network_name_length, subnet_cidr):
        network_create_args = {
            "name": self._generate_random_name(
                prefix=consts.NETWORK_NAME_PREFIX,
                length=network_name_length)}
        subnet_create_args = {
            "name": self._generate_random_name(
                prefix=consts.SUBNETWORK_NAME_PREFIX,
                length=network_name_length)
        }
        network, subnets = self._create_network_and_subnets(
            network_create_args=network_create_args,
            subnet_create_args=subnet_create_args,
            subnets_per_network=1,
            subnet_cidr_start=subnet_cidr)
        return network["network"]

    def boot_server_with_network_and_attach_volume(
            self, image, flavor, network, server_name_length, volume_size,
            volume_name_length, **kwargs):
        server_name = self._generate_random_name(
            prefix=consts.SERVERS_NAME_PREFIX, length=server_name_length)
        volume_name = self._generate_random_name(
            prefix=consts.VOLUME_NAME_PREFIX, length=volume_name_length)

        volume = self._create_volume(volume_size, display_name=volume_name)
        server = self._boot_server(image, flavor, name=server_name,
                                   nics=[{"net-id": network["id"]}], **kwargs)

        self._attach_volume(server, volume)


class MoxScenarios(key_utils.KeystoneScenario):
    RESOURCE_NAME_PREFIX = consts.KEYSTONE_NAME_PREFIX

    @types.set(image=types.ImageResourceType,
               flavor=types.FlavorResourceType)
    @validation.required_openstack(users=True)
    @scenario.configure(
        context={"cleanup": ["nova", "neutron", "keystone, cinder"],
                 "admin_cleanup": ["keystone", "nova", "neutron, cinder"]})
    def boot_server_with_network_in_single_tenant(
            self, image, flavor, volume_size=1, tenant_name_length=10,
            user_name_length=10, network_name_length=10, server_name_length=10,
            volume_name_length=10, subnet_cidr="1.0.0.0/24", **kwargs):
        """Create and attach volume

        Create a tenant, network, subnet, volume, boot a server from an
        image and attach volume to it.

        :param image: image to be used to boot an instance
        :param flavor: flavor to be used to boot an instance
        :param volume_size: volume size (in GB)
        :param tenant_name_length: length of the random part of tenant name
        :param user_name_length: length of the random part of user name
        :param network_name_length: length of the random part of network name
        :param server_name_length: length of the random part of server name
        :param volume_name_length: length of the random part of volume name
        :param subnet_cidr: str, start value for subnets CIDR
        :param kwargs: Optional additional arguments for server creation

        """

        tenant = self._tenant_create(name_length=tenant_name_length,
                                     **kwargs)
        user = self._user_create(tenant_id=tenant.id,
                                 password=consts.USER_PASSWORD,
                                 name_length=user_name_length)
        new_endpoint = objects.Endpoint(
            auth_url=self.context["user"]["endpoint"].auth_url,
            username=user.name, password=consts.USER_PASSWORD,
            tenant_name=tenant.name)
        helper = NovaAndNeutronHelper(
            context=self.context,
            admin_clients=self._admin_clients,
            clients=osclients.Clients(new_endpoint))
        helper._atomic_actions = self._atomic_actions

        network = helper.create_network_with_subnet(network_name_length,
                                                    subnet_cidr)

        helper.boot_server_with_network_and_attach_volume(
            image, flavor, network, server_name_length, volume_size,
            volume_name_length, **kwargs)
