# coding: utf-8
from rally_reports.base import TemplateJinjaReport


class HtmlReport(TemplateJinjaReport):
    """Class for HTML report"""
    template = 'rally_report.html'

    # default query, fetch min,median,max and group by every field.
    query = (
        "SELECT min(value),median(value),max(value) "
        "FROM rally "
        "WHERE jenkins_build_number =~ /.*/ "
        "AND mos_iso =~ /.*/ "
        "AND task_created_at =~ /.*/ "
        "GROUP BY * fill(none)"
    )

    def serialize_data(self):
        """Serialize ResultSet and adapt to our needs.

        :return:
        """
        res = super(HtmlReport, self).serialize_data()
        data = {}

        for point in res:
            uuid = point['uuid']
            atomic_name = point['atomic_name']

            if uuid not in data:
                data[uuid] = {
                    'task_name': point['task_name'] or uuid,
                    'build': point['jenkins_build_number'],
                    'uuid': uuid,
                    'environment_label': point['environment_label'],
                    'deployment_id': point['deployment_id'],
                    'time': point['task_created_at'],
                    'iso': point['mos_iso'],
                    'result': self._get_status(point),
                    'actions': {},
                }

            if atomic_name and atomic_name in data[uuid]['actions']:
                raise Exception("Error, atomic_name already exist")

            if atomic_name:
                data[uuid]['actions'][atomic_name] = {
                    'atomic_name': atomic_name,
                    'max': point['max'],
                    'median': point['median'],
                    'min': point['min']
                }

        return data

    def _get_status(self, point):
        """Calculate SLA status"""
        sla_success = point.get('sla_success')

        if sla_success == '' or sla_success == 'True':
            sla_success = True
        else:
            sla_success = False

        status = point.get('status')

        if status == 'finished' and sla_success:
            return 'ok'
        elif status == 'finished' and not sla_success:
            return 'failed'
        elif status == 'aborted':
            return 'interrupted'
        elif status == 'failed':
            return 'error'

        raise AttributeError('status is not recognized!!!')
