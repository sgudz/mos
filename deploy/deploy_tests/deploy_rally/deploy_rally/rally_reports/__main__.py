# coding: utf-8
from __future__ import absolute_import

import argparse

import influxdb

from .report_html import HtmlReport  # NOQA
from .report_rst import RST_REPORT_FABRIC  # NOQA


def parse_args():
    """Parse args"""
    parser = argparse.ArgumentParser()
    parser.add_argument('--influxdb-connection',
                        help='Connection string to InfluxDB')
    parser.add_argument('--deployment',
                        help='Rally deployment name')
    parser.add_argument('--html-file',
                        help='Path to HTML file which should contain the data'
                             'output')
    parser.add_argument('--rst-file',
                        help='Path to RST file which should contain the data'
                             'output')
    parser.add_argument('--rst-report-type',
                        help='Report type to generate rst. \
                        Can be performance or density')
    parser.add_argument('--astute-yaml',
                        help='Path to astyte.yaml file')
    opts = parser.parse_args()

    if not opts.influxdb_connection:
        parser.error("You must specify '--influxdb-connection' string!")

    if not opts.deployment:
        parser.error("You must specify '--deployment' string!")

    return opts


def main():
    """Entry point of app."""
    opts = parse_args()

    connection = influxdb.InfluxDBClient.from_DSN(opts.influxdb_connection)
    print_std = True
    if opts.html_file:
        print_std = False
        HtmlReport(connection, opts).save_as_file(opts.html_file)

    if opts.rst_file and opts.rst_report_type:
        print_std = False
        try:
            RST_REPORT_FABRIC[opts.rst_report_type](
                connection, opts).generate_report()
        except KeyError:
            raise Exception("Unknown rst report type")

    if print_std:
        return HtmlReport(connection, opts).render()


if __name__ == "__main__":
    main()
