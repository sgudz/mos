class BasePowerDriver(object):
    def power_status(self, ip, name, username, password):
        raise NotImplementedError("Should have implemented this")

    def power_off(self, ip, name, username, password):
        raise NotImplementedError("Should have implemented this")

    def power_on(self, ip, name, username, password):
        raise NotImplementedError("Should have implemented this")
