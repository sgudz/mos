#!/opt/stack/.venv/bin/python

import argparse
import collections
import datetime
import json
import logging
import os
import random
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import uuid
import yaml

from prettytable import PrettyTable
from subunit import v2 as subunit_v2
from testtools.testresult.real import UTC
from xml.dom import minidom

# NOTE(akurilin): this script is designed for mos-scale lab, so usage
# hardcoded variables instead of parsing input args is not bad idea.
SMOKE = os.getenv('SMOKE', '0')
LOAD_FACTOR = os.getenv('LOAD_FACTOR', '1')
COMPUTE = os.getenv('COMPUTE', '1')
CONTROLLER = os.getenv('CONTROLLER', '1')
CONCURRENCY = os.getenv('CONCURRENCY', '5')
SIM_RUNS = int(os.getenv('SIM_RUNS', '1'))
SHAKER_RUN = os.getenv('SHAKER_RUN', 'false')
SKIP_ON_BIG_SCALE = os.getenv('SKIP_ON_BIG_SCALE', '0')
MAIN_DIR = '/opt/stack'
RALLY_SCENARIOS = '{0}/rally-scenarios'.format(MAIN_DIR)
EXECUTOR_SETTINGS = '{0}/executor_settings.json'.format(MAIN_DIR)
LOG_DIR = '/var/log/job-reports'
BIN_DIR = '{0}/.venv/bin'.format(MAIN_DIR)
SKIP_FILE = '{0}/.venv/etc/skip_test.txt'.format(MAIN_DIR)
SKIP_FILE_LIGHT = '{0}/.venv/etc/skip_test_light.txt'.format(MAIN_DIR)
SKIP_FILE_BIG_SCALE = '{0}/.venv/etc/skip_test_big_scale.txt'.format(MAIN_DIR)
CONCURRENCY_FILE = '{0}/.venv/etc/concurrency.yaml'.format(MAIN_DIR)
VENV_PYTHON = "{0}/rally".format(BIN_DIR)
RUN_UUID = str(uuid.uuid4())[:8]
TAG = '{0}/{1}/{2}'.format(os.getenv('JOB_NAME', 'manual'),
                           os.getenv('BUILD_NUMBER', 'manual'),
                           RUN_UUID)
BOOL_2_SMILE = {False: ':(', True: ':)'}
GLOBAL_TIMEOUT = os.getenv('GLOBAL_TIMEOUT', 86400)
RALLY_VERSION = os.getenv("RALLY_VERSION", "master")
ABORT_ON_SLA_FAILURE = os.getenv("ABORT_ON_SLA_FAILURE", False)
FUEL_VERSION = int(os.getenv('FUEL_VERSION', '8.0')[0])
SAHARA_IMAGE_UUID = os.getenv("SAHARA_IMAGE_UUID", None)
dev_null = open(os.devnull, 'w')


def _avg(arr):
    return sum(arr) / len(arr)


def _make_temp(prefix):
    fd, name = tempfile.mkstemp(prefix=prefix)
    # close returned file descriptor to avoid fd leaks
    os.close(fd)
    return name


def _test_id_suffix(metadata):
    suffix = ''
    runner = metadata.get('kw').get('runner')
    if runner:
        suffix += ' [%s iterations, %s threads]' % (
            runner.get('times') or 1,
            runner.get('concurrency') or 1)
    return suffix


def _process_non_json_data(data, output, test_id):
    """Processed data returned in non-JSON format.

    This usually happens in case if task was failed, and Rally doesn't return
    any json to parse.
    """
    output.startTestRun()
    try:
        output.status(test_id=test_id,
                      file_name='rally-stderr',
                      mime_type='text/plain; charset="utf8"',
                      eof=True,
                      file_bytes=data.encode('utf8'))
        status = 'fail'
        if data.find('Service is not available') >= 0:
            status = 'skip'
        output.status(test_id=test_id, test_status=status)
    except Exception as e:
        output.status(test_id='rally2subunit',
                      test_status='fail',
                      file_name='stderr',
                      mime_type='text/plain; charset="utf8"',
                      file_bytes='Exception: %s' % e)
    output.stopTestRun()
    return 1


def _process_iterations(output, scenario_result, test_id, start_time):
    """Goes through all iterations of scenario result and processes them."""
    output.startTestRun()
    output.status(test_id=test_id, test_status='inprogress',
                  timestamp=start_time)
    scenario_config_str = json.dumps(scenario_result['key'], indent=2,
                                     separators=(',', ': '))
    output.status(test_id=test_id,
                  file_name='config',
                  mime_type='text/plain; charset="utf8"',
                  eof=True,
                  file_bytes=scenario_config_str.encode('utf8'))

    iteration_results = scenario_result['result']
    total_iterations = len(iteration_results)
    scenario_success = total_iterations > 0
    scenario_failures = 0
    actions = collections.defaultdict(list)

    for iteration in range(total_iterations):
        one_result = iteration_results[iteration]

        actions['~total'].append(one_result['duration'])
        for atomic_action, duration in \
                one_result['atomic_actions'].items():
            if duration:
                actions[atomic_action].append(duration)

        if one_result['error']:
            scenario_failures += 1
            scenario_success = False
            output.status(test_id=test_id,
                          file_name='stderr-%04d' % iteration,
                          mime_type='text/plain; charset="utf8"',
                          eof=True,
                          file_bytes='\n'.join(
                              one_result['error']).encode('utf8'))
    return actions, scenario_failures, scenario_success, total_iterations


def rally_to_subunit(data, test_id, output_file):
    """Is used while report generation."""
    tmp_output_file = open(output_file, mode='a+')
    output = subunit_v2.StreamResultToBytes(tmp_output_file)
    logging.debug('Subunit output file is {0}'.format(output_file))

    try:
        task_result = json.loads(data)
    except ValueError:
        return _process_non_json_data(data, output, test_id)

    # if task was successfully processed
    for scenario_result in task_result:
        test_id += _test_id_suffix(scenario_result['key'])
        start_time = datetime.datetime.now(UTC())

        actions, scenario_failures, scenario_success, total_iterations = \
            _process_iterations(output, scenario_result, test_id, start_time)

        expected_runs = scenario_result['key']['kw']['runner']['times']

        table = PrettyTable(['Action', 'min', 'avg', 'max', 'failures',
                             'total', 'result'])
        table.float_format = "6.3"

        for key in sorted(actions.keys()):
            d = actions[key]
            min_value = min(d)
            max_value = max(d)
            avg_value = _avg(d)
            failures = expected_runs - len(d)
            success = failures == 0

            if key == '~total':
                success = scenario_success
                failures = scenario_failures

            table.add_row([key, min_value, avg_value, max_value,
                           failures, total_iterations, BOOL_2_SMILE[success]])

        output.status(test_id=test_id,
                      file_name='results',
                      mime_type='text/plain; charset="utf8"',
                      eof=True,
                      file_bytes=table.get_string().encode('utf8'))

        end_time = start_time
        if total_iterations:
            end_time += datetime.timedelta(seconds=_avg(actions['~total']))

        if scenario_success:
            test_status = 'success'
        else:
            test_status = 'fail'

        output.status(test_id=test_id, test_status=test_status,
                      timestamp=end_time)
        output.stopTestRun()
    tmp_output_file.close()
    return 0


def _find_rally_scenarios(scenarios_path):
    tmp_scenarios = []
    scenarios = []
    for root_dir, dirnames, filenames in os.walk(scenarios_path):
        for filename in filenames:
            if filename.endswith(('.yaml', '.json')):
                tmp_scenarios.append(os.path.join(root_dir, filename))
    logging.debug('Found rally scenarios: {0}'.format(len(tmp_scenarios)))
    skipped_scenarios = []
    with open(SKIP_FILE, 'r') as skip_file:
        logging.debug('Skip scenarios from {0}'.format(SKIP_FILE))
        for line in skip_file:
            if not line.startswith("#"):
                skipped_scenarios.append(line.strip())

    if int(SMOKE) != 0:
        logging.info('Smoke run detected, scenarios from {0} '
                     'skipping also'.format(SKIP_FILE_LIGHT))
        with open(SKIP_FILE_LIGHT, 'r') as skip_file_light:
            for line in skip_file_light:
                if not line.startswith("#"):
                    skipped_scenarios.append(line.strip())

    if int(SKIP_ON_BIG_SCALE) != 0:
        logging.debug('Skip scenarios from {0}'.format(SKIP_FILE_BIG_SCALE))
        with open(SKIP_FILE_BIG_SCALE, 'r') as skip_file_big_scale:
            for line in skip_file_big_scale:
                if not line.startswith("#"):
                    skipped_scenarios.append(line.strip())

    for scenario in tmp_scenarios:
        skip = False
        for skipped_scenario in skipped_scenarios:
            if skipped_scenario and skipped_scenario in scenario:
                logging.info('** Skip ** {0}'.format(skipped_scenario))
                skip = True
                break
        if skip is False:
            scenarios.append(scenario)
    random.shuffle(scenarios)
    logging.debug('Not skipped Rally scenarios without: {0}'.format(
        len(scenarios)))
    return scenarios


def _prepare_values_for_template(template):
    range_regex = "([\d\.]+)-([\d\.]+)$"
    re_range = re.compile(range_regex)

    segmentation_type = "gre"
    vlan_amount = 1025
    floating_ip_amount = 25

    try:
        with open("/root/cluster.cfg") as f:
            for line in f.readlines():
                if line.startswith("net_segment_type"):
                    segmentation_type = line.split("=")[1].strip()
                if line.startswith("floating_"):
                    res = re_range.search(line)
                    if "vlan" in line:
                        vlan_amount = int(res.group(2)) - int(res.group(1))
                    else:
                        # calculate the maximum number
                        # of floating ip addresses
                        # 1 is subtracted due to assigning
                        # one address to the router_04 interface
                        ip_to_int = [struct.unpack("!I",
                                     socket.inet_aton(i))[0]
                                     for i in res.group(1, 2)]
                        floating_ip_amount = (int(ip_to_int[1]) -
                                              int(ip_to_int[0]) - 1)

    except IOError:
        logging.error("cluster.cfg was not found, achtung!")

    values = {'controller': CONTROLLER,
              'compute': COMPUTE,
              'concurrency': CONCURRENCY,
              'sahara_image_uuid': SAHARA_IMAGE_UUID,
              'current_path': os.path.dirname(os.path.abspath(template)),
              "gre_enabled": segmentation_type == "gre",
              "vlan_amount": vlan_amount,
              "floating_ip_amount": floating_ip_amount,
              "floating_net": 'admin_floating_net' if FUEL_VERSION > 7
              else 'net04_ext'}
    logging.debug(values)

    def operator(op):
        if int(SMOKE) != 0:
            return 1
        elif LOAD_FACTOR:
            return op * int(LOAD_FACTOR)
        return op

    for k, v in values.items():
        if isinstance(v, basestring):
            if v.isdigit():
                values[k] = operator(int(v))

    return json.dumps(values)


def _cmd_run(cmd, log_suffix='', stdout=True):
    logging.debug('Try to run {}'.format(cmd))
    main_cmd = os.path.basename(cmd[1])
    if main_cmd == '':
        main_cmd = 'unknown'
    if stdout:
        f_stdout = _make_temp('current-{0}-output-'.format(main_cmd))
        f_error = _make_temp(prefix='current-{0}-error-'.format(main_cmd))
        f_out = open(f_stdout, 'w+')
        f_err = open(f_error, 'w+')
        logging.debug('{2} run output file is {0}. '
                      '{2} run error file is {1}'.format(f_stdout, f_error,
                                                         main_cmd))
        cmd_run = subprocess.Popen(cmd, stdout=f_out, stderr=f_err,
                                   close_fds=True)
        return cmd_run, f_stdout, f_error, f_out, f_err
    else:
        output_log = open('{0}/{1}-{2}-stdout.log'.format(
            LOG_DIR, log_suffix, main_cmd), 'w+')
        cmd_run = subprocess.Popen(cmd, stdout=output_log, stderr=output_log,
                                   close_fds=True)
        return cmd_run


def _cmd_run_wait_output(commands, log_suffix='', rally=False):
    if rally:
        cmd_run, f_stdout, f_error, f_out, f_err = _rally_run(
            commands, log_suffix=log_suffix)
    else:
        cmd_run, f_stdout, f_error, f_out, f_err = _cmd_run(
            commands, log_suffix=log_suffix)
    logging.debug('Waiting command')
    cmd_run.wait()
    f_out = open(f_stdout, 'r')
    f_err = open(f_error, 'r')
    output = f_out.read()
    err = f_err.read()
    f_out.close()
    f_err.close()
    return output, err


def _rally_run(commands, log_suffix='', stdout=True):
    cmd = ['{0}/python'.format(BIN_DIR), '{0}/rally'.format(BIN_DIR), 'task']
    for command in commands:
        cmd.append(command)
    if commands[0].find('start') == 0:
        cmd += ['--tag', TAG]
    rally_run = _cmd_run(cmd, log_suffix, stdout)
    return rally_run


def start_shaker():
    logging.info('Start shaker test full_l3_east_west.yaml')
    cmd = ['/bin/bash', '{0}/shaker_prepare_and_loop'.format(BIN_DIR),
           '/opt/stack/shaker-scenarios/networking/full_l3_east_west.yaml']
    shaker_run = _cmd_run(cmd)
    # Commented to SIGINT shaker support
    # _cmd_run_wait_output(cmd, log_suffix='shaker_prepare')
    # logging.info('Start shaker, report must be on '
    #              '/var/log/job-reports/shaker_report.html '
    #              'after end')
    # cmd = ['{0}/python'.format(BIN_DIR), '{0}/shaker'.format(BIN_DIR),
    #        '--debug', '--scenario',
    #        '/opt/stack/shaker-scenarios/networking/full_l3_east_west.yaml',
    #        '--report', '/var/log/job-reports/shaker_report.html']
    # shaker_run = _cmd_run(cmd)
    return shaker_run[0]


def stop_shaker(shaker_run):
    logging.info('Stop shaker')
    shaker_run.send_signal(signal.SIGINT)


def _rally_run_wait_output(commands, log_suffix=''):
    output, err = _cmd_run_wait_output(commands, log_suffix, rally=True)
    return output, err


def _get_last_task_id():
    """Returns last task ID.

    Rally's output after listing the tasks returns them in the following
    format:
    2015-02-02 15:45:23.769 25088 RALLYDEBUG <some debug>
    2015-02-02 15:45:23.770 25088 INFO rally.common.utils [-] <some info>
    ...
    2015-02-02 15:45:23.771 25088 INFO rally.common.utils [-] <some info>
    +---------+-----------------+-------------+-------------+----------+-----+
    | uuid    | deployment_name | created_at  | duration    | status   | tag |
    +---------+-----------------+-------------+-------------+----------+-----+
    | <uuid1> | <name1>         | <datetime1> | <duration1> | finished |     |
    | <uuid2> | <name1>         | <datetime2> | <duration2> | finished |     |
    | <uuid3> | <name2>         | <datetime3> | <duration3> | finished |     |
    | <uuid4> | <name2>         | <datetime4> | <duration4> | finished |     |
    +---------+-----------------+-------------+-------------+----------+-----+
    """
    output, err = _rally_run_wait_output(['list'])
    rally_status = [job for job in output.splitlines() if TAG in job]
    task_line = rally_status[-1].split('|')
    last_id = task_line[1]
    last_id.strip()
    logging.debug('Last task id is {0}'.format(last_id))
    return last_id


def _get_running_tasks():
    """Returns last task ID.

    Rally's output after listing the tasks returns them in the following
    format:
    2015-02-02 15:45:23.769 25088 RALLYDEBUG <some debug>
    2015-02-02 15:45:23.770 25088 INFO rally.common.utils [-] <some info>
    ...
    2015-02-02 15:45:23.771 25088 INFO rally.common.utils [-] <some info>
    +---------+-----------------+-------------+-------------+----------+-----+
    | uuid    | deployment_name | created_at  | duration    | status   | tag |
    +---------+-----------------+-------------+-------------+----------+-----+
    | <uuid1> | <name1>         | <datetime1> | <duration1> | finished |     |
    | <uuid2> | <name1>         | <datetime2> | <duration2> | finished |     |
    | <uuid3> | <name2>         | <datetime3> | <duration3> | finished |     |
    | <uuid4> | <name2>         | <datetime4> | <duration4> | finished |     |
    +---------+-----------------+-------------+-------------+----------+-----+
    Currently a tag is assigned for a test run, so we can filter all output by
    tag and grab the last line.
    """
    running_statuses = {
        'running', 'verifying', 'init', 'setting up', 'cleaning up',
        'aborting', 'soft_aborting'
    }

    output, err = _rally_run_wait_output(['list'])
    rally_tasks = output.splitlines()
    running_rally_tasks = []
    all_tasks = 0
    for task in rally_tasks:
        if TAG not in task:
            continue
        task_data = [column.strip() for column in task.split('|')]
        all_tasks += 1
        if task_data[-3] in running_statuses:
            running_rally_tasks.append(task_data[1].strip())
    logging.debug('Running tasks found - {0}'.format(running_rally_tasks))
    logging.debug('All tasks {0}'.format(all_tasks))
    return running_rally_tasks, all_tasks


def rally_run_return_task_id(scenario):
    _, tasks_before_run = _get_running_tasks()
    scenario_name = os.path.basename(scenario)[0:-5]
    scenario_folder = os.path.basename(
        os.path.normpath(os.path.dirname(scenario)))
    start_args = ['start',
                  '--task-args',
                  _prepare_values_for_template(scenario),
                  scenario]
    if ABORT_ON_SLA_FAILURE:
        start_args.append("--abort-on-sla-failure")
    _rally_run(start_args,
               log_suffix=scenario_folder + "_" + scenario_name,
               stdout=False)
    logging.debug('Run task {0}'.format(scenario_name))
    time.sleep(2)
    _, tasks_after_run = _get_running_tasks()
    timeout = 60
    count = 0
    while tasks_after_run == tasks_before_run:
        _, tasks_after_run = _get_running_tasks()
        time.sleep(1)
        count += 1
        if count > timeout:
            logging.error('*** Something wrong *** Rally task does '
                          'not started during more than 60 '
                          'seconds. Please check log '
                          '{0}/{1}-rally-stdout.log'.format(LOG_DIR,
                                                            scenario_name))
            return None
    task_id = _get_last_task_id()
    task_id = task_id.strip()
    return task_id


def generate_skipped_file(xml_file):
    xml_doc = minidom.parse(xml_file)
    item_list = xml_doc.getElementsByTagName('testcase')
    skipped_file = open('{0}/skipped-tests.txt'.format(LOG_DIR), 'w+')
    for test_case in item_list:
        if test_case.getElementsByTagName('skipped'):
            skipped_file.write('{}.{} - SKIPPED\n'.format(
                test_case.attributes['classname'].value,
                test_case.attributes['name'].value))
    skipped_file.close()


def _execute_bash_script(cmds, prefix):
    script = _make_temp(prefix=prefix)
    script_file = open(script, 'w+')
    for cmd in cmds:
        script_file.write('{0}\n'.format(cmd))
    script_file.close()
    logging.debug('Execute /bin/bash {0}'.format(script))
    start_script = subprocess.Popen(['/bin/bash', script],
                                    stdout=dev_null, stderr=dev_null)
    start_script.wait()
    return True


def gzip_logs():
    _execute_bash_script(['gzip {0}/*.log'.format(LOG_DIR)], 'gzip-logs')
    return True


def generate_xml_report(tasks_id, output_file):
    logging.info('Generate xml (junut) report to {0}'.format(output_file))
    tmp_subunit = _make_temp('subunit-')
    for key in tasks_id:
        logging.debug('Generate subunit for {0}'.format(key))
        output, _ = _rally_run_wait_output(['results', key],
                                           log_suffix='generate_xml')
        t_class = tasks_id[key].split('/')
        test_class = 'rally-scenarios.{0}.{1}'.format(
            t_class[-2], t_class[-1].split('.')[0])
        logging.debug('Test class is {0}'.format(test_class))
        # when Rally task fails it doesn't produce json
        try:
            json.loads(output)
        except ValueError:
            logging.debug('Empty json from rally, try to get rally detailed')
            output, _ = _rally_run_wait_output(
                ['detailed', key], log_suffix='generate_xml')
            rally_to_subunit(output, test_class, tmp_subunit)
        else:
            logging.debug('Json ok')
            rally_to_subunit(output, test_class, tmp_subunit)
    cmd = '{0}/python {0}/subunit2junitxml < {1} > {2}'.format(
        BIN_DIR, tmp_subunit, output_file)
    _execute_bash_script([cmd], 'xml_generate_script-')
    return True


def generate_rally_report(tasks_id, output_file):
    logging.info('Generate rally report to {0}'.format(output_file))
    cmd = ['report', '--tasks']
    for key in tasks_id:
        cmd.append(key)
    cmd.append('--out')
    cmd.append(output_file)
    rally_ran, _, _, _, _ = _rally_run(cmd, log_suffix='generate_results')
    rally_ran.wait()
    return 0


def _find_running_scenarios(running_tasks, all_tasks):
    scenarios = []
    logging.debug('Running tasks are {0}'.format(running_tasks))
    logging.debug('All tasks are {0}'.format(all_tasks))
    for key in all_tasks:
        for running_task in running_tasks:
            if key == running_task:
                logging.debug(all_tasks[key])
                scenarios.append("/".join(all_tasks[key].split('/')[-2:]))
    logging.debug('Services under load are {0}'.format(scenarios))
    return scenarios


def _find_services_under_load(running_scenarios, test_concur):
    services_under_load = set()
    for scenario in running_scenarios:
        logging.debug('Scenario run: {0}'.format(scenario))
        if scenario in test_concur:
            services_under_load |= test_concur[scenario]["services"]
    return services_under_load


def _check_if_there_is_exclusive_scenario(running_scenarios, test_concur):
    locked = False
    for scenario in running_scenarios:
        if scenario in test_concur:
            locked |= not test_concur[scenario]["parallel"]
    return locked


def _find_next_scenario(scenarios, running_scenarios, light, test_concur):

    next_scenario = None
    logging.debug(
        'Concurrent services runned: {0}, locking task: {1}'.
        format(_find_services_under_load(running_scenarios, test_concur),
               _check_if_there_is_exclusive_scenario(running_scenarios,
                                                     test_concur)))

    for scenario in scenarios:
        scen_name = "/".join(scenario.split('/')[-2:])
        if len(running_scenarios) >= SIM_RUNS:
            break
        if scen_name in test_concur:
            loaded_services = _find_services_under_load(running_scenarios,
                                                        test_concur)
            exclusive_scenario_used = _check_if_there_is_exclusive_scenario(
                running_scenarios, test_concur)
            if (scen_name in test_concur and
               not test_concur[scen_name]["services"] & loaded_services and
               test_concur[scen_name]["parallel"] and
               not exclusive_scenario_used):
                next_scenario = scenario
            elif (len(running_scenarios) == 0
                  and not test_concur[scen_name]["parallel"]):
                next_scenario = scenario
            elif len(running_scenarios) == 0 or light:
                next_scenario = scenario
        elif len(running_scenarios) == 0 or light:
            next_scenario = scenario
        if next_scenario is not None:
            break

    return next_scenario


def start_parallel_run(scenarios, test_concur):
    id_all_running_tasks = {}
    while len(scenarios) > 0:
        current_running_tasks, _ = _get_running_tasks()
        logging.debug('We have {0} running tasks'
                      'and {1} scenarios in queue'.format(
                          len(current_running_tasks),
                          len(scenarios)))
        services_under_load = _find_services_under_load(
            _find_running_scenarios(current_running_tasks,
                                    id_all_running_tasks),
            test_concur)
        logging.info('Try to find task for free service')
        next_scenario = _find_next_scenario(
            scenarios,
            _find_running_scenarios(current_running_tasks,
                                    id_all_running_tasks),
            bool(int(SMOKE)),
            test_concur)
        if next_scenario is not None:
            logging.info('Services under load are {0}'.format(
                ",".join(services_under_load)))
            logging.info('Adding new task {0}'.format(next_scenario))
            scenarios.remove(next_scenario)
            task_id = rally_run_return_task_id(next_scenario)
            logging.info('Added new task {0}'.format(next_scenario))
            if task_id is not None:
                id_all_running_tasks[task_id] = next_scenario
            current_running_tasks_tmp, _ = _get_running_tasks()
            services_under_load_tmp = _find_services_under_load(
                _find_running_scenarios(current_running_tasks,
                                        id_all_running_tasks),
                test_concur)
            logging.info('Now services under load are {0}'.format(
                ",".join(services_under_load_tmp)))
            logging.info('Now we have {0}'
                         ' running tasks, '
                         'and {1} scenarios in queue'.format(
                             len(current_running_tasks_tmp),
                             len(scenarios)))
            logging.info('Waiting free slot...')
        else:
            logging.info("Can't find scenario in queue for free service, "
                         "will try again after 2 seconds")
        time.sleep(60)

    logging.debug('All tasks started in this run: {0}'.format(
        id_all_running_tasks))
    return id_all_running_tasks


def wait_all_running_tasks(timeout=86400):
    current_running_tasks = _get_running_tasks()
    logging.info('Waiting running {0} '
                 'tasks.'.format(current_running_tasks[0]))
    count = 0
    while len(current_running_tasks) > 0:
        time.sleep(60)
        count += 60
        logging.debug('Waiting running tasks {0}'.format(count))
        if count > timeout:
            raise RuntimeError('Waiting running tasks timeout')
        current_running_tasks, _ = _get_running_tasks()
    logging.info('All tasks finished')
    return 0


def process_results(tasks_id):
    generate_rally_report(tasks_id, '{0}/rally_report.html'.format(LOG_DIR))
    generate_xml_report(tasks_id, '{0}/rally-report.xml'.format(LOG_DIR))
    generate_skipped_file('{0}/rally-report.xml'.format(LOG_DIR))


def main():
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    ch = logging.StreamHandler(sys.stdout)
    fh = logging.FileHandler('{0}/run_rally-debug.log'.format(LOG_DIR))
    ch.setLevel(logging.INFO)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    fh.setFormatter(formatter)
    root.addHandler(ch)
    root.addHandler(fh)

    parser = argparse.ArgumentParser(description='Run rally tests')
    parser.add_argument('--task',
                        dest='scenario',
                        default='all',
                        help='single scenario or scenarios path')
    args = parser.parse_args()
    scenario = args.scenario
    shaker = None
    if SHAKER_RUN == 'true':
        shaker = start_shaker()
    if scenario.find('all') == 0:
        scenarios = _find_rally_scenarios(RALLY_SCENARIOS)
        logging.info('Start scenarios from {0}'.format(RALLY_SCENARIOS))
    elif os.path.isdir(scenario):
        scenarios = _find_rally_scenarios(scenario)
        logging.info('Start scenarios from {0}'.format(scenario))
    elif os.path.isfile(scenario):
        scenarios = [scenario]
        logging.info('Start scenarios from {0}'.format(scenario))
    else:
        raise RuntimeError('Can\'t find path {0}'.format(scenario))
    logging.info('You can find debug log in '
                 '{0}/run_rally-debug.log'.format(LOG_DIR))

    with open(CONCURRENCY_FILE) as concur_file:
        concur_yaml = yaml.load(concur_file)
        test_concur = {}
        for service in concur_yaml:
            for scenario_name in concur_yaml[service]:
                scenario_info = concur_yaml[service][scenario_name].split(' ')
                parallel = bool(int(scenario_info[0]))

                services = ({''} if len(scenario_info) == 1
                            else set(scenario_info[1].split(',')))

                test_concur['%s/%s' % (service, scenario_name)] = {
                    "parallel": parallel,
                    "services": services,
                }

    with open(EXECUTOR_SETTINGS, "w") as settings_file:
        settings_file.write(json.dumps({
            "executor_version": RALLY_VERSION,
            "type": os.getenv("EXECUTION_TYPE", "scale"),
            "concurrency": 0,
            "shaker_run": SHAKER_RUN
        }))

    tasks_id = start_parallel_run(scenarios, test_concur)
    wait_all_running_tasks(timeout=GLOBAL_TIMEOUT)
    if SHAKER_RUN == 'true':
        stop_shaker(shaker)
        # TBD: add time logs for scenario runs in to the shaker report html
    process_results(tasks_id)
    gzip_logs()


if __name__ == '__main__':
    main()
