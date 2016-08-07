"""
===============================================================================
WHAT THIS SCRIPT DOES?
-------------------------------------------------------------------------------
This script is designed to generate report-page based on jobs results.

Template for generated report-page: ./templates/summary_report.html
NOTE: path to template can be changed in variables HTML_TEMPLATE_DIR (template
      location) and OUTPUT_HTML_REPORT (name of template file)

===============================================================================
HOW DOES THIS SCRIPT WORK?
-------------------------------------------------------------------------------

# function ``main`` -> function ``_import_matplotlib``
Step 1: Check that "matplotlib" library is installed. This library is too big
        itself and requires a lot of other libraries, so it is not set in
        project requirements list.

# function ``main`` -> function ``get_tests``
Step 2: discover all information about tests and sort it by executors name

# function ``get_tests``
Step 2.1: search for *.xml files in EXECUTION_RESULTS directory

# function ``get_tests`` -> function ``_parse_filename``
Step 2.2: parse full-path to found files (look at docstring of
          ``_parse_filename`` for more details)

# function ``get_tests`` -> function ``_parse_junit``
Step 2.3: parse each found xml-file with junit parser

# function ``get_tests`` -> function ``_parse_cluster_settings``
Step 2.4: obtain information about OpenStack components and storage while
          parsing cluster settings from "settings_1.yaml" (located in each root
          directory of found *.xml file).

# function ``get_tests`` -> function ``_parse_executor_settings``
Step 2.4: obtain executor settings(executor_version, execution_type and
          concurrency) from "settings_1.yaml" (located in each root
          directory of found *.xml file)

# function ``get_tests`` -> function ``_get_node_number``
Step 2.6: parse number of nodes from "number_of_nodes" (located in each root
          directory of found *.xml file)

# function ``get_tests``
Step 2.6: sort test results by date of job ended

# function ``main`` -> function ``generate_plots``
Step 3: generate plots based on test results
Step 3.1: generate plot for tempest
Step 3.2: generate plot for rally

# function ``main`` -> function ``generate_html``
Step 4: render html-report based on discovered data

===============================================================================
"""

import ConfigParser
import collections
import logging
import os
import re

import jinja2
import xunitparser
import yaml

from datetime import timedelta

plt = None

# NOTE(akurilin): this script is designed for mos-scale lab, so usage
# hardcoded variables instead of parsing input args is not bad idea.
JENKINS_HOSTNAME = "http://172.20.8.32"
NGINX_HOSTNAME = "http://172.20.9.32"
EXECUTION_RESULTS = "/var/lib/volumes/test_results"
OUTPUT_HTML_REPORT = "/var/lib/volumes/test_results/index.html"

HTML_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates")
HTML_TEMPLATE = "summary_report.html"

EXECUTORS_RESULTS_TEMPLATE = {"rally": "standard_results_table.html",
                              "tempest": "standard_results_table.html",
                              "shaker": "shaker_results_table.html"}


def _import_matplotlib():
    """Try import 'matplotlib' and print user-friendly message if it missed."""
    global plt
    try:
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib import pyplot

        plt = pyplot
    except ImportError:
        logging.error(
            "%s requires 'matplotlib' library. "
            "You can install it using following command: \n\t"
            "pip install matplotlib" % __file__)
        return 1


def _parse_filename(filename):
    """Filename parser.

    Expected format for filename:
        <site_url>/test_results/<first_info_part>/<second_info_part>

      Format of <first_info_part>:
        build_<build_number>_<optional_build_info>

      Format of <second_info_part>:
        jenkins-<job_name>-<job_id>-<os>-<time_zone>-
        <start-year>-<start-month>-<start-day>-<start-hours>-<start-minutes>-<start-seconds>-
        <end-year>-<end-month>-<end-day>-<end-hours>-<end-minutes>-<end-seconds>

    Returns a dict with parsed data.
    """
    print("Start parsing '%s'" % filename)

    match = re.match(
        r"%s/build_(?P<build>['a-z0-9.-]+)[a-zA-Z0-9_.:-]*/"
        r"jenkins-(?P<job_name>[a-z0-9_]+)-(?P<job_id>\d+)-"
        r"(?P<job_os>\w+)-(?P<time_zone>\w+)-(?P<dates>[0-9:-]+)" %
        EXECUTION_RESULTS, filename)

    if not match:
        logging.error("Invalid filename in '%s', skipped." % filename)
        return
    else:
        data = match.groupdict()

        job_name = data.pop("job_name")
        for executor in EXECUTORS_RESULTS_TEMPLATE.keys():
            if job_name.find(executor) > -1:
                data["executor"] = executor
        if not data.get("executor"):
            # NOTE(akurilin): HTML template is not designed for "unknown"
            # executor, so let's skip such tests for now.
            return

        job_id = data.pop("job_id")
        data["jenkins_job"] = {
            "url": "/".join(["%s:8080" % JENKINS_HOSTNAME,
                             "job", job_name, job_id]),
            "name": ("%s-%s" % (job_name, job_id)).replace("'", "")}

        date_match = re.match(
            r"(?P<start_year>\d+)-(?P<start_month>\d+)-(?P<start_day>\d+)-"
            r"(?P<start_hours>\d+)-(?P<start_minutes>\d+)-"
            r"(?P<start_seconds>\d+)-"
            r"(?P<end_year>\d+)-(?P<end_month>\d+)-(?P<end_day>\d+)-"
            r"(?P<end_hours>\d+)-(?P<end_minutes>\d+)-(?P<end_seconds>\w+)",
            data.pop("dates", None))

        if not date_match:
            logging.error("Invalid date format in '%s', skipped." % filename)
            return

        date = date_match.groupdict()
        data["job_start_date"] = (
            "%(start_year)s/%(start_month)s/%(start_day)s "
            "%(start_hours)s-%(start_minutes)s-%(start_seconds)s" % date)
        data["job_end_date"] = (
            "%(end_year)s/%(end_month)s/%(end_day)s "
            "%(end_hours)s-%(end_minutes)s-%(end_seconds)s" % date)

        data["results_url"] = filename.replace(
            EXECUTION_RESULTS, os.path.join(NGINX_HOSTNAME, "test_results"))

        return data


def _parse_junit(filename):
    """JUnit parser."""
    try:
        ts, tr = xunitparser.parse(open(filename))
        notime = timedelta(0)
        skipped = len([tc for tc in ts if tc.time == notime and tc.failed])
        return {"tests": ts.countTestCases(),
                "failures": len(tr.failures) - skipped,
                "skipped": skipped,
                "errors": len(tr.errors)}
    except Exception as err:
        logging.error("Incorrect file: '%s'i: %s", filename, err)
        return {"tests": "-",
                "failures": "-",
                "skipped": "-",
                "errors": "-"}


def _parse_cluster_settings(root_dir):
    components = []
    storages = []
    job_os = ""

    parser = ConfigParser.SafeConfigParser()
    settings_file = os.path.join(root_dir, "cluster.cfg")
    try:
        parser.read(settings_file)
        cluster_settings = dict(parser.items('cluster'))
        components = ['{0}+{1}'.format(
            cluster_settings.get('net_provider', 'neutron'),
            cluster_settings.get('net_segment_type', 'unknown')),
            'heat']
        for service in ['ceilometer', 'sahara', 'murano']:
            if 'true' in cluster_settings.get(service, ''):
                components.append(service)
        storages = []
        for storage in ['volumes_lvm', 'images_ceph', 'ephemeral_ceph']:
            if 'true' in cluster_settings.get(storage, ''):
                storages.append(storage)
        release = cluster_settings.get('release_name', '').lower()
        job_os = 'centos' if release.startswith('centos') else 'ubuntu'
    except ConfigParser.Error as error:
        logging.error(error)

    return {"components": ','.join(map(str, components)),
            "storage": ','.join(map(str, storages)),
            "job_os": job_os}


def _parse_executor_settings(root_dir):
    filename = os.path.join(root_dir, "executor_settings.json")
    settings = None
    try:
        with open(filename, 'r') as stream:
            settings = yaml.load(stream)
    except IOError:
        logging.error("Invalid executor settings in '%s'." % filename)

    return settings if settings else {
        "executor_version": "no info",
        "type": "no info",
        "concurrency": 1,
        "shaker_run": "no info", }


def _get_node_number(root_dir):
    """Returns number of nodes parsed from <root>/number_of_nodes file."""

    if os.path.isfile(os.path.join(root_dir, "cluster.cfg")):
        filename = os.path.join(root_dir, "cluster.cfg")
        parser = ConfigParser.SafeConfigParser()
        parser.read(filename)
        cluster_settings = dict(parser.items('cluster'))
        return (int(cluster_settings.get('controller_count')) +
                int(cluster_settings.get('compute_count')))
    else:
        filename = os.path.join(root_dir, "number_of_nodes")
        try:
            with open(filename, 'r') as f:
                return f.read().replace('\n', '')
        except IOError:
            logging.error("Nodes number is missed in: '%s'" % filename)
            return "no info"


def _listdir(path, depth):
    tree = {}
    for f in os.listdir(path):
        full_path = os.path.join(path, f)
        if os.path.isdir(full_path) and depth > 0:
            tree.update(_listdir(full_path, depth - 1))
        else:
            tree[path] = tree.get(path, []) + [f]
    return tree


def get_tests():
    """Grab and return dict of tests.

    Finds all results in $EXECUTION_RESULTS directory and returns a
    `collections.OrderedDict`, where keys are executors names and values
    contain list of discovered executions.

    NOTE:
        1) `collections.OrderedDict` is used to display results in expected
            order.
        2) each list of discovered executions is sorted by end-date
    """

    tests = {}
    files = _listdir(EXECUTION_RESULTS, 2)
    for root in files:
        if root.endswith('theme'):
            continue
        if filter(lambda filename: filename.endswith(".xml") or
                  filename.endswith(".html"), files[root]):
            execution = {}

            parsed_filename = _parse_filename(root)
            if not parsed_filename:
                continue
            execution.update(parsed_filename)
            junit_file = os.path.join(root,
                                      "%s_report.xml" % execution["executor"])
            execution.update(_parse_junit(junit_file))
            cluster_data = _parse_cluster_settings(root)
            execution["components"] = cluster_data["components"]
            execution["storage"] = cluster_data["storage"]
            if not execution.get("job_os", None) and cluster_data["job_os"]:
                execution["job_os"] = cluster_data["job_os"]

            execution["job_nodes"] = _get_node_number(root)

            execution.update(_parse_executor_settings(root))

            if execution["executor"] not in tests:
                tests[execution["executor"]] = []
            tests[execution["executor"]].append(execution)

    for executor in tests:
        tests[executor].sort(key=lambda x: x["job_end_date"])

    return collections.OrderedDict(sorted(tests.iteritems(),
                                          key=lambda x: x[0]))


def _generate_plot(graph, title, color, tests, key):
    _tests = [test[key] for test in tests if test[key] != "-"]
    graph.fill_between(range(0, len(_tests)), 0, _tests,
                       facecolor=color, interpolate=True)
    graph.set_title(title)
    graph.set_xlim([0, len(_tests) - 1])


def generate_plots(tests, executor, display_failed=True,
                   display_skipped=True):
    subplots_number = sum([display_failed, display_skipped]) + 1
    fig, g = plt.subplots(subplots_number, 1, sharex=True)
    graphs = list(g)

    _generate_plot(graphs.pop(0), "All %s tests" % executor, "green",
                   tests[executor], "tests")

    if display_failed:
        _generate_plot(
            graphs.pop(0), "Failed %s tests" % executor, "red",
            tests[executor], "failures")

    if display_skipped:
        _generate_plot(
            graphs.pop(0), "Skipped %s tests" % executor, "yellow",
            tests[executor], "skipped")

    plt.savefig('%s/%s' % (EXECUTION_RESULTS, executor))


def generate_html(tests):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(HTML_TEMPLATE_DIR))
    rendered_template = env.get_template(HTML_TEMPLATE).render(
        tests=tests, executors_results_template=EXECUTORS_RESULTS_TEMPLATE)
    with open(OUTPUT_HTML_REPORT, "w") as html_file:
        html_file.write(rendered_template)


def main():
    matplotlib_status = _import_matplotlib()
    if matplotlib_status > 0:
        return matplotlib_status

    tests = get_tests()
    # generate_plots(tests, "tempest")

    # NOTE(akurilin): skipped tests is not displayed. I don't know why,
    #                 but assume that because of the fact that Rally doesn't
    #                 skip tests.
    generate_plots(tests, "rally", display_skipped=False)

    generate_html(tests)


if __name__ == '__main__':
    main()
