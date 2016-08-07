# coding: utf-8
from os.path import dirname, abspath, join  # NOQA

import jinja2

from rally_reports.utils import flat_resultset

TEMPLATE_BASE_DIR = join(dirname(abspath(__file__)), 'templates')


class Report(object):
    """Base class for report"""
    def __init__(self, db, options):
        self.options = options
        self.db = db

    def serialize_data(self):
        """Abstract method for serialize data

        :return: dict
        """
        raise NotImplementedError()

    def render(self):
        """Abstract method for render data

        :return: str
        """
        raise NotImplementedError()

    def save_as_file(self, filename):
        """Save prepared data from self.render to file

        :param filename:
        :return:
        """
        with open(filename, 'w') as fp:
            fp.write(self.render())


class TemplateJinjaReport(Report):
    """Base class for template report """
    template = None
    query = "select * from rally where environment_label={deployment}"

    def get_template(self):
        """Get the template for this object

        :return: jinja template object
        """
        j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
            TEMPLATE_BASE_DIR), trim_blocks=True)

        return j2_env.get_template(self.template)

    def get_result_set(self):
        """Get influxdb query ResultSet from remote server

        :return: ResultSet
        """
        if not self.query:
            raise ValueError('query is empty!')

        query = self.query.format(deployment=self.options.deployment)
        return self.db.query(query)

    def serialize_data(self):
        """Serialize a ResultSet by returning its attributes.

        :return:
        """
        result_set = self.get_result_set()
        data = flat_resultset(result_set)
        return data

    def render(self):
        """Render the object to string from template. Default engine Jija.

        :return:
        """
        template = self.get_template()
        data = self.serialize_data()

        return template.render(results=data)

    def save_as_file(self, filename):
        """Render and save result to file.

        :param filename:
        :return:
        """
        with open(filename, 'wb') as fp:
            fp.write(self.render().encode('utf-8'))
