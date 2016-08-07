# -*- coding: utf-8 -*-


from __future__ import print_function

import csv
import itertools
import json
import sys

import yaml
import clusterdb


class App(object):

    observable = True

    @classmethod
    def install_parser(cls, parsers):
        parser = cls.create_parser(parsers)
        if parser:
            parser.set_defaults(callback=cls)

        return parser

    @classmethod
    def create_parser(cls, parsers):
        pass

    @classmethod
    def all_apps(cls):
        classes = cls.__subclasses__()
        classes.extend(itertools.chain.from_iterable(
            kls.all_apps() for kls in list(classes)))
        classes = filter(lambda kls: kls.observable, classes)

        return classes

    def __init__(self, options):
        self.debug = options.debug
        self.session_maker = clusterdb.session_factory(options.db_connection)

    def do(self):
        pass


class ListApp(App):

    CSV_FIELDS = []

    observable = False

    @classmethod
    def install_parser(cls, parsers):
        parser = cls.create_parser(parsers)
        if parser:
            parser.set_defaults(callback=cls)

        parser = super(ListApp, cls).install_parser(parsers)

        parser.add_argument(
            "-f", "--format",
            help="Format for output.",
            choices=("json", "json-pp", "csv", "csv-pp", "yaml"),
            default="json-pp")

        return parser

    def __init__(self, options):
        super(ListApp, self).__init__(options)

        self.format = options.format

    def get_info(self):
        return {}

    def do(self):
        info = self.get_info()

        if self.format == "json":
            print(json.dumps(info))
        elif self.format == "json-pp":
            print(json.dumps(
                info,
                sort_keys=True,
                indent=4))
        elif self.format == "yaml":
            print(yaml.safe_dump(
                info,
                default_flow_style=False,
                allow_unicode=True,
                width=79,
                indent=4))
        elif self.format in ("csv", "csv-pp"):
            writer = csv.DictWriter(sys.stdout, self.CSV_FIELDS)
            if self.format == "csv-pp":
                writer.writeheader()
            writer.writerows(self.info_to_csv(info))
