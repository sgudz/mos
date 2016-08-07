import math

from rally.task import sla
from rally.common.i18n import _


@sla.configure(name="max_ninety_percentile")
class MaxNinetyPercentile(sla.SLA):
    """Maximum allowed 90%ile value."""

    CONFIG_SCHEMA = {
        "type": "number", "minimum": 0.0, "exclusiveMinimum": True
    }

    def __init__(self, criterion_value):
        super(MaxNinetyPercentile, self).__init__(criterion_value)
        self.durations = []

    def _percentile(self, arr, perc):
        a = sorted(arr)
        k = (len(a) - 1) * perc
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            return a[int(k)]
        d0 = a[int(f)] * (c - k)
        d1 = a[int(c)] * (k - f)
        return d0 + d1

    def add_iteration(self, iteration):
        if iteration.get("error"):
            return self.success

        self.durations.append(iteration["duration"])
        if len(self.durations) == 1:
            self.success = self.durations[0] <= self.criterion_value
        else:
            perc = self._percentile(self.durations, 0.9)
            self.success = perc <= self.criterion_value

        return self.success

    def merge(self, other):
        self.durations.append(other.durations)
        perc = self._percentile(self.durations, 0.9)
        self.success = perc <= self.criterion_value
        return self.success

    def details(self):
        return (_("%(status)s - Maximum allowed ninety percentile "
                  "in seconds: %(sec).2f") %
                {"status": self.status(), "sec": self.criterion_value})
