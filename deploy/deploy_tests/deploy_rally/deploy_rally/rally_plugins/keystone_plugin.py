
import uuid

from rally.plugins.openstack import scenario
from rally.plugins.openstack.scenarios.keystone import utils as key_utils
from rally.task import atomic


class KeystonePlugin(key_utils.KeystoneScenario):
    @atomic.action_timer("create_role")
    def _create_role(self):
        """Creates keystone user role with random name.

        :param name_length: length of generated (random) part of role name
        :returns: keystone user role instance
        """

        role = self.admin_clients("keystone").roles.create(
            self.generate_random_name())
        return role

    @atomic.action_timer("authenticate")
    def _authenticate(self):
        """Authenticate against the server.

        Normally this is called automatically when you first access the API,
        but you can call this method to force authentication right now.

        Returns on success; raises :exc:`exceptions.Unauthorized` if the
        credentials are wrong.
        """

        password = uuid.uuid4().hex
        self.admin_clients("keystone").authenticate(username='test',
                                                    password=password)

    @atomic.action_timer("assign_role")
    def _role_assign(self, user, role, tenant):
        self.admin_clients("keystone").roles.add_user_role(user, role, tenant)

    @atomic.action_timer("update_user_password")
    def _update_user_password(self, password, user_id):
        self.admin_clients("keystone").users.update_password(user_id,
                                                             password)

    @atomic.action_timer("update_tenant")
    def _update_tenant(self, tenant):
        description = tenant.name + "_description_updated_" + uuid.uuid4().hex
        name = tenant.name + "_updated"
        self.admin_clients("keystone").tenants.update(tenant.id,
                                                      name, description)

    @atomic.action_timer("delete_tenant")
    def _delete_tenant(self, tenant):
        self.admin_clients("keystone").tenants.delete(tenant.id)

    @atomic.action_timer("remove_role")
    def _role_remove(self, user, role, tenant):
        self.admin_clients("keystone").roles.remove_user_role(user,
                                                              role, tenant)

    @atomic.action_timer("list_roles")
    def _list_roles_for_user(self, user, tenant):
        self.admin_clients("keystone").roles.roles_for_user(user, tenant)

    @atomic.action_timer("get_tenant")
    def _get_tenant(self, tenant):
        self.admin_clients("keystone").tenants.get(tenant.id)

    @atomic.action_timer("get_user")
    def _get_user(self, user):
        self.admin_clients("keystone").users.get(user.id)

    @atomic.action_timer("get_role")
    def _get_role(self, role):
        self.admin_clients("keystone").roles.get(role.id)

    @atomic.action_timer("get_service")
    def _get_service(self, service_id):
        self.admin_clients("keystone").services.get(service_id)

    @atomic.action_timer("service_list")
    def _service_list(self):
        return self.admin_clients("keystone").services.list()

    @atomic.action_timer("delete_role")
    def _delete_role(self, role):
        self.admin_clients("keystone").roles.delete(role)

    @atomic.action_timer("create_service")
    def _create_service(self, name, service_type, description):
        return self.admin_clients("keystone").services.create(name,
                                                              service_type,
                                                              description)

    @atomic.action_timer("delete_service")
    def _delete_service(self, service):
        try:
            self.admin_clients("keystone").services.delete(service)
        except Exception:
            pass

    def _get_service_id(self, name):
        for i in self._service_list():
            if i.name == name:
                return i.id

    def _remove_services(self):
        for i in self._service_list():
            if i.name.startswith("rally_test_service_"):
                self._delete_service(i.id)

    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def assign_and_remove_user_role(self):
        tenant = self._tenant_create()
        user = self._user_create()
        role = self._create_role()
        self._role_assign(user, role, tenant)
        self._role_remove(user, role, tenant)

    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_delete_role(self):
        role = self._create_role()
        self._delete_role(role)

    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def get_entities(self):
        tenant = self._tenant_create()
        user = self._user_create()
        role = self._create_role()
        self._get_tenant(tenant)
        self._get_user(user)
        self._get_role(role)
        self._get_service(self._get_service_id("keystone"))

    @scenario.configure()
    def get_token(self):
        self._authenticate()

    @scenario.configure()
    def create_and_list_user_roles(self):
        tenant = self._tenant_create()
        user = self._user_create()
        role = self._create_role()
        self._role_assign(user, role, tenant)
        self._list_roles_for_user(user, tenant)

    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def update_user_password(self):
        password = uuid.uuid4().hex
        user = self._user_create()
        self._update_user_password(password, user.id)

    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def update_and_delete_tenant(self):
        tenant = self._tenant_create()
        self._update_tenant(tenant)
        self._delete_tenant(tenant)

    @scenario.configure(context={"admin_cleanup": ["keystone"]})
    def create_and_delete_service(self):
        name = "rally_test_service_" + uuid.uuid4().hex
        service_type = "rally_test_type"
        description = "rally_test_service_description_" + uuid.uuid4().hex
        service = self._create_service(name, service_type, description)
        self._delete_service(service.id)
        self._remove_services()
