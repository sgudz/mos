import copy
import imp
import os

from rally.common import objects
from rally import osclients
from rally.plugins.openstack.cleanup import base
from rally.plugins.openstack.cleanup import resources
from rally.plugins.openstack.wrappers import keystone as keystone_wrapper


consts = imp.load_source(
    "consts",
    os.path.join(os.path.abspath(__file__).rsplit("/", 1)[0], "consts.py"))


@base.resource("nova", "mox_servers", order=next(resources._nova_order),
               admin_required=True)
class MOXNovaServer(base.ResourceManager):
    def _manager(self):
        return self.admin.nova().servers

    def delete(self):
        if getattr(self.raw_resource, "OS-EXT-STS:locked", False):
            self.raw_resource.unlock()
        super(MOXNovaServer, self).delete()

    def list(self):
        # NOTE(andreykurilin): nova list returns only 1000 servers at once,
        # so we need to list all tenants to find all resources
        keystone = keystone_wrapper.wrap(self.admin.keystone())
        tenants = filter(
            lambda res: res.name.startswith(consts.KEYSTONE_NAME_PREFIX),
            keystone.list_projects())

        servers = []
        users = keystone.list_users()
        for tenant in tenants:
            user = filter(lambda user: user.project_id == tenant.id, users)[0]
            kw = copy.deepcopy(self.admin.endpoint.to_dict())
            kw.update({"tenant_name": tenant.name, "username": user.name,
                       "password": consts.USER_PASSWORD})
            clients = osclients.Clients(objects.Endpoint(**kw))
            # NOTE(andreykurilin): test tenant should contain only test
            # resources, so we can ignore check of name.
            # Check should look like:
            #     server.name.startswith(consts.SERVERS_NAME_PREFIX)
            servers.extend(clients.nova().servers.list())
        return servers


@base.resource(service=None, resource=None, admin_required=True)
class MOXNeutronMixin(resources.NeutronMixin):

    RESOURCE_PREFIX = ""

    def delete(self):
        res_name = self._resource.replace("mox_", "")
        delete_method = getattr(self._manager(), "delete_%s" % res_name)
        delete_method(self.id())

    def list(self):
        res_name = self._resource.replace("mox_", "") + "s"
        list_method = getattr(self._manager(), "list_%s" % res_name)
        resources = list_method()[res_name]
        return [res for res in resources
                if res["name"].startswith(self.RESOURCE_PREFIX)]


@base.resource("neutron", "mox_subnet", order=next(resources._neutron_order),
               tenant_resource=True, admin_required=True)
class NeutronSubnet(MOXNeutronMixin):
    RESOURCE_PREFIX = consts.SUBNETWORK_NAME_PREFIX


@base.resource("neutron", "mox_network", order=next(resources._neutron_order),
               tenant_resource=True, admin_required=True)
class NeutronNetwork(MOXNeutronMixin):
    RESOURCE_PREFIX = consts.NETWORK_NAME_PREFIX


class KeystoneMixin(resources.KeystoneMixin, base.ResourceManager):
    def delete(self):
        res_name = self._resource.replace("mox_", "")
        delete_method = getattr(self._manager(), "delete_%s" % res_name)
        delete_method(self.id())

    def list(self):
        res_name = self._resource.replace("mox_", "") + "s"
        list_method = getattr(self._manager(), "list_%s" % res_name)

        return [res for res in list_method()
                if res.name.startswith(consts.KEYSTONE_NAME_PREFIX)]


@base.resource("keystone", "mox_user", order=next(resources._keystone_order),
               admin_required=True, perform_for_admin_only=True)
class KeystoneUser(KeystoneMixin):
    pass


@base.resource("keystone", "mox_project",
               order=next(resources._keystone_order), admin_required=True,
               perform_for_admin_only=True)
class KeystoneProject(KeystoneMixin):
    pass


@base.resource("cinder", "mox_volumes", order=next(resources._cinder_order),
               admin_required=True)
class CinderVolume(base.ResourceManager):
    def list(self):
        servers = self._manager().list(search_opts={"all_tenants": 1})
        return [s for s in servers
                if s.display_name.startswith(consts.VOLUME_NAME_PREFIX)]
