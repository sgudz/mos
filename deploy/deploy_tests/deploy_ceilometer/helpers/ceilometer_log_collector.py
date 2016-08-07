#!/usr/bin/env python

# Copyright 2014: Mirantis Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import glob
import mako.template
import operator
import os
from os import path
import sys


YAXIS_LABELS = {'cpu': 'Used CPU, percents',
                'mem': 'Used memory, percents',
                'vsize': 'Size of used virtual memory, GB',
                'physical_size': 'Size of used physical memory, GB',
                'iostat': 'IOStat util, %',
                'mongoio': 'Samples are written per second'}

DIV_HTML = ("<div id='results' class='{name}'>"
            "<h3>{title}</h3>"
            "<svg class='{name}'></svg>"
            "</div>\n")

TITLES = {'cpu': 'Used CPU',
          'mem': 'Memory used',
          'vsize': 'Virtual memory used',
          'physical_size': 'Physical memory used',
          'iostat': 'IOStat util',
          'mongoio': 'MongoDB. Writes sample per second'}


def get_pstat_file_prefix(file):
    """Get prefix of log file.

    File name format is <node_name>[-prefix]-<type>.log
    """
    return file.rsplit("-", 2)[-2]


def get_nodename(file):
    """Get nodename of log file.

    File name format is <node_name>[-prefix]-<type>.log
    """
    name = path.basename(file)
    return name.rsplit("-", 1)[0]


def get_log_type(file):
    """Get type of log file.

    File name format is <node_name>[-prefix]-<type>.log
    """
    name = path.basename(file)
    return name.rsplit("-", 1)[-1][:-4]


def transform_raw_values(times, raw_values, granularity):
    """Calculate harmonic mean with granularity."""
    values = []
    max_value = 0
    for i in range(0, len(raw_values), granularity):
        sub_values = raw_values[i:i + granularity]
        m = len(sub_values) / reduce(lambda x, y:
                                     x + 1. / (y or len(sub_values)),
                                     sub_values, 0)
        t = times[i]
        max_value = max(m, max_value)
        values.append([t, m])
    return values


class Logs(object):
    """Class for log data."""
    def __init__(self, name, label, title, time_granularity=20):
        self.values = []
        self.label = label
        self.max_value = 0
        self.name = name
        self.title = title
        self.time_granularity = time_granularity / 2

    def add_value(self, times, raw_values, nodename, raw_format=False):
        """Add values from log file.

        Values format is [[<timestamp>, <value>], ...]
        """
        if raw_values:
            if not raw_format:
                values = transform_raw_values(times, raw_values,
                                              self.time_granularity)
            else:
                values = [[times[i], raw_values[i]] for i in range(len(times))]
            self.max_value = max(max(values, key=operator.itemgetter(1))[1],
                                 self.max_value)

            self.values.append({'values': values,
                                'key': nodename})

    def as_dict(self):
        return {'yaxis_label': self.label, 'name': self.name,
                'max_y': self.max_value, 'value': self.values}


class LogCollector(object):
    """Class to collect logs from log files."""
    def __init__(self, time_granularity=20):
        self.logs = {}
        self.time_granularity = time_granularity

    def collect_logs(self, directories):
        for directory in directories:
            if os.path.isdir(directory):
                for file in glob.glob(directory + "/*.log"):
                    self.parse(file)

    def _get_log(self, log_type, prefix=None):
        log_name = "%s-%s" % (prefix, log_type) if prefix else log_type
        title = TITLES.get(log_type)
        if prefix:
            prefix = prefix[0].upper() + prefix[1:]
            title = "%s. %s" % (prefix, title)

        return self.logs.get(log_name,
                             Logs(log_name,
                                  YAXIS_LABELS.get(log_type),
                                  title,
                                  self.time_granularity))

    def _parse_psstat_file(self, file):
        firts_ts = 0
        prefix = get_pstat_file_prefix(file)
        values = [[], [], [], []]
        times = []
        with open(file, 'r') as f:
            lines = f.readlines()
            sums = [0, 0, 0, 0]
            for line in lines:
                line = line.strip()
                parts = [part for part in line.split(" ") if part]
                if len(parts) == 1:
                    if not firts_ts:
                        firts_ts = int(parts[0])
                        continue
                    for i in range(len(values)):
                        if i in [2, 3]:
                            sums[i] /= 2 ** 20
                        values[i].append(sums[i])
                    times.append(int(parts[0]) - firts_ts)
                    sums = [0, 0, 0, 0]
                else:
                    sums = [
                        sums[i] + float(parts[i]) for i in range(len(sums))]

        log_types = ['cpu', 'mem', 'vsize', 'physical_size']
        nodename = get_nodename(file)
        for i, log_type in enumerate(log_types):
            self._write_log(log_type, nodename, times, values[i], prefix)

    def _parse_iostat_file(self, file):
        time = 0
        times = []
        values = []
        with open(file, 'r') as f:
            lines = f.readlines()
            iterator = iter(lines)
            try:
                while True:
                    line = iterator.next().strip()
                    disks = line.split(":")
                    try:
                        for i, disk in enumerate(disks):
                            util = float(disk.strip())
                            if len(values) <= i:
                                values.append([])
                            values[i].append(util)
                    except ValueError:
                        pass
                    time += 2
                    times.append(time)
            except StopIteration:
                pass
        nodename = get_nodename(file)
        log_type = 'iostat'
        for i, value in enumerate(values):
            self._write_log(log_type, nodename, times, value, "disk%s" % i)

    def _parse_mongoio_file(self, file):
        first_timestamp = None
        values = []
        times = []
        with open(file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                line = line.strip()
                parts = [int(part) for part in line.split(" ")]
                timestamp = parts[0]
                value = parts[1]
                if not first_timestamp:
                    first_timestamp = timestamp
                values.append(value)
                times.append(timestamp - first_timestamp)
        nodename = get_nodename(file)
        log_type = 'mongoio'
        self._write_log(log_type, nodename, times, values)
        self._write_log(log_type, nodename, times, values, 'raw', True)

    def _write_log(self, log_type, nodename, times, values, log_prefix=None,
                   raw_format=False):
        log = self._get_log(log_type, log_prefix)
        log.add_value(times, values, nodename, raw_format)
        self.logs[log.name] = log

    def parse(self, file):
        """Find correct function to parse log file.

        Function name in format "_parse_<type>_file".
        """
        log_type = get_log_type(file)
        func_name = "_parse_%s_file" % log_type
        func = getattr(self, func_name)
        if func:
            try:
                func(file)
            except Exception:
                pass


def main(args):
    parser = argparse.ArgumentParser("Ceilometer logs collector and formater")
    parser.add_argument(
        "-d",
        dest='directories',
        default='/tmp/ceilometer_logs',
        nargs='+',
        help="Directories with log files"
    )
    parser.add_argument(
        "-o",
        dest='output',
        default='/tmp/ceilometer_logs/results.html',
        help='Output file')
    parser.add_argument(
        "-t",
        dest='template',
        default='templates/ceilometer-results.mako',
        help='Template file')
    parser.add_argument(
        "--time_granularity",
        dest='granularity',
        default=30,
        type=int,
        help='Template file')

    args = parser.parse_args(args)
    directories = (args.directories if type(args.directories) is list
                   else [args.directories])
    collector = LogCollector(args.granularity)
    collector.collect_logs(directories)

    with open(args.template) as template:
        template = mako.template.Template(template.read())
    with open(args.output, 'w+') as result_html:
        divs = [DIV_HTML.format(name=name, title=collector.logs[name].title)
                for name in sorted(collector.logs)]
        result_html.write(
            template.render(data=[log.as_dict()
                                  for log in collector.logs.values()],
                            divs="\n".join(divs)))


if __name__ == "__main__":
    main(sys.argv[1:])
