import platform
from datetime import datetime

import influxdb
from rally import api
from rally import consts
from rally import exceptions
from rally.common import logging
from rally.common.plugin import plugin
from rally.task import exporter
from six.moves.urllib import parse as urlparse


LOG = logging.getLogger(__name__)


def configure(name, namespace="default"):
    return plugin.configure(name=name, namespace=namespace)


@configure(name="influxdb")
class InfluxdbExporter(exporter.TaskExporter):
    """Exporter plugin for influxDB"""
    MEASUREMENT = "rally"
    A_MEASUREMENT = "annotations"

    def __init__(self, connection_string):
        super(InfluxdbExporter, self).__init__(connection_string)
        self.validate(connection_string)

        self.connection = influxdb.InfluxDBClient.from_DSN(connection_string)
        self.precision = 'ms'

        self.task = None
        self.hostname = platform.node()

    def validate(self, connection_string=None):
        """Validate connection string.

        The format of connection string in influxdb plugin is
        influxdb://username:pass@localhost:8086/databasename
        """
        parse_obj = urlparse.urlparse(connection_string)
        if connection_string is None or (parse_obj.netloc == "" or
                                         parse_obj.path == ""):
            raise exceptions.InvalidConnectionString(
                "It should be "
                "`influxdb://username:pass@host:port/databasename`.")

    def finished_task(self):
        """Compute task in finished status

        :return:
        """
        res = list()
        tasks_data = [{"key": x["key"], "results": x["data"]["raw"],
                       "full_duration": x['data']['full_duration'],
                       "sla": x['data']['sla']}
                      for x in self.task.get_results()]

        task_created_at = self.task['created_at'].date()

        for data in tasks_data:
            task_name = data['key']['name']
            sla_success = self.check_sla(data['sla'])

            for result in data['results']:
                if 'atomic_actions' in result and result['atomic_actions']:
                    # Increment timestamp by duration
                    timestamp = result['timestamp']
                    atomic_actions = result['atomic_actions']

                    for name, duration in atomic_actions.iteritems():
                        res.append({
                            "measurement": self.MEASUREMENT,
                            "tags": {
                                "uuid": self.task['uuid'],
                                "task_name": task_name,
                                "atomic_name": name,
                                "hostname": self.hostname,
                                "status": self.task['status'],
                                "sla_success": sla_success,
                                "task_created_at": task_created_at
                            },
                            "time": datetime.fromtimestamp(timestamp),
                            "fields": {
                                "value": duration
                            }
                        })

                        timestamp += duration
                else:
                    duration = data['full_duration']
                    timestamp = self.task['created_at']

                    res.append({
                        "measurement": self.MEASUREMENT,
                        "tags": {
                            "uuid": self.task['uuid'],
                            "task_name": task_name,
                            "status": self.task['status'],
                            "hostname": self.hostname,
                            "sla_success": sla_success,
                            "task_created_at": task_created_at,
                        },
                        "time": timestamp,
                        "fields": {
                            "value": duration
                        }
                    })
        return res

    def _get_data(self):
        """Build data for write in influxdb.

        :return: list result to write in influxdb
        """
        # defaults
        timestamp = self.task['created_at'].isoformat()
        task_created_at = self.task['created_at'].date()

        res = list()
        res.append(self.annotate(self.task, timestamp, start=True))

        if self.task['status'] == consts.TaskStatus.FINISHED:
            res += self.finished_task()

        elif self.task['status'] in (consts.TaskStatus.FAILED,
                                     consts.TaskStatus.ABORTED):
            # failed status don't have duration, calculate it
            duration = self.task['updated_at'] - self.task['created_at']
            duration = duration.total_seconds()

            # Failed task haven't task name. When launch task run, we need
            # setup task tag as task_name.
            task_name = self.task.get('tag', 'none')

            res.append({
                "measurement": self.MEASUREMENT,
                "tags": {
                    "uuid": self.task['uuid'],
                    "task_name": task_name,
                    "hostname": self.hostname,
                    "status": self.task['status'],
                    "sla_success": False,
                    "task_created_at": task_created_at,
                },
                "time": timestamp,
                "fields": {
                    "value": duration
                }
            })
        else:
            msg = ("Task %s results would be available when it will "
                   "finish, aborted, or failed." % self.task['uuid'])
            raise exceptions.RallyException(msg)

        res.append(self.annotate(self.task, self.task['updated_at']))

        return res

    def export(self, uuid):
        """Export results of the task to the influxdb.

        :param uuid: uuid of the task object
        """
        self.task = api.Task.get(uuid)
        deployment = api.Deployment.get(self.task['deployment_uuid'])
        merged_tags = {}

        try:
            conf = deployment['config']
            merged_tags['deployment_id'] = conf['fuel_env']['environment_id']

            mos_iso = conf['fuel_env'].get('mos_iso', 'none')
            merged_tags['mos_iso'] = mos_iso

            jenkins_build_number = conf['fuel_env']['jenkins_build_number']
            merged_tags['jenkins_build_number'] = jenkins_build_number

            # if env_label is empty set default value
            env_label = conf['fuel_env']['environment_label']
            env_label = env_label or 'env-{}'.format(
                merged_tags['deployment_id'])
            merged_tags['environment_label'] = env_label

        except KeyError:
            raise Exception("You must provide 'environment_label', "
                            "'jenkins_build_number', and "
                            "'environment_id' in 'fuel_env' section of "
                            "deployment config.")

        data = self._get_data()

        self.connection.write_points(data, time_precision=self.precision,
                                     tags=merged_tags)

    def annotate(self, task, timestamp, start=False):
        """Compute annotate

        :param task:
        :param timestamp:
        :param start:
        :return:
        """
        # Hardcode status for start point
        status = task['status']
        if start is True:
            status = 'starting'

        data = 'uuid={}'.format(task['uuid'])

        return {
            'time': timestamp,
            'measurement': self.A_MEASUREMENT,
            'tags': {
                'cluster': 'rally',
                'tags': 'rally',
            },
            'fields': {
                'title': "status is {}".format(status),
                'text': data
            }
        }

    def check_sla(self, data):
        """Check sla status.

        If at least one status is False, check not passed and return False
        Else return True
        :param data: list of sla data
        :return: bool
        """
        # search sucess=False, and then check it.
        if [v for v in data if not v["success"]]:
            return False

        return True
