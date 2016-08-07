#!/usr/bin/env python

#
# Need to install fuelclient as
#  pip install git+git://git.openstack.org/openstack/python-fuelclient.git
#
# Testrail API description:
#  http://docs.gurock.com/testrail-api2/start
#

import os
import sys

from settings import TestRailSettings
from testrail_client import TestRailProject

import re

from fuelclient.client import APIClient

from oslo_config import cfg
try:
    import rally.common.db.api as rally_db
except ImportError:
    import rally.db.api as rally_db


CONF = cfg.CONF


JENKINS_JOB = os.environ.get('JOB_NAME') + '/' + os.environ.get('BUILD_NUMBER')


def main():

    cluster_description = os.environ.get('BUILD_URL') + '\n---\n'

    # Get Fuel version
    fuel_version = APIClient.get_request("version")
    cluster_description += 'Fuel version: {}-{}\n\n'.format(
        fuel_version['release'], fuel_version['build_number']
    )

    # Fuel cluster is needed only to get releases
    fuel_cluster = APIClient.get_request("clusters")[0]
    # Release contains info about operating system
    fuel_release = APIClient.get_request("releases/{}".format(
        fuel_cluster['release_id'])
    )
    cluster_description += 'Cluster configuration: {}\n\n'.format(
        fuel_release['name']
    )

    # Networking parameters
    cluster_network = APIClient.get_request(
        "clusters/{}/network_configuration/neutron".format(
            fuel_cluster['id']
        )
    )
    # Network segmentation
    cluster_ns = cluster_network['networking_parameters']['segmentation_type']
    cluster_description += 'Network segmentation: {}\n\n'.format(
        cluster_ns
    )

    # Cluster nodes
    controllers = 0
    computes = 0
    for node in APIClient.get_request("nodes"):
        if(node['cluster'] == fuel_cluster['id']):
            if('controller' in node['roles']):
                controllers += 1
            if('compute' in node['roles']):
                computes += 1
    cluster_description += 'Total nodes:   {}\n'.format(controllers + computes)
    cluster_description += '+ controllers: {}\n'.format(controllers)
    cluster_description += '+ computes:    {}\n\n'.format(computes)

    # Other cluster options
    cluster_attributes = APIClient.get_request(
        "clusters/{}/attributes".format(
            fuel_cluster['id']
        )
    )
    addn_components = cluster_attributes['editable']['additional_components']
    cluster_optionalcomponents = []
    for opt_comp in ['ceilometer', 'heat', 'murano', 'sahara']:
        if(addn_components[opt_comp]['value']):
            cluster_optionalcomponents.append(opt_comp)
    cluster_description += 'Optional components: {}\n\n'.format(
        ', '.join(cluster_optionalcomponents)
    )

    # Storage
    cluster_storage = []
    for opt_stor in ['ephemeral_ceph', 'images_ceph', 'objects_ceph',
                     'volumes_ceph', 'volumes_lvm']:
        if(cluster_attributes['editable']['storage'][opt_stor]['value']):
            cluster_storage.append(opt_stor)
    cluster_description += 'Storage: {}\n'.format(
        ', '.join(cluster_storage)
    )

    # Display Fuel info and cluster configuration
    print(cluster_description)

    # Initialize TestRail
    project = TestRailProject(
        url=TestRailSettings.url,
        user=TestRailSettings.user,
        password=TestRailSettings.password,
        project=TestRailSettings.project
    )

    # Find milestone
    for ms in project.get_milestones():
        if(ms['name'] == fuel_version['release']):
            milestone = ms
            break
    print('Testrail milestone: {}'.format(milestone['name']))

    # Find configs
    for cf in project.get_configs():
        if(cf['name'] == 'Operation System'):
            for ccf in cf['configs']:
                if(ccf['name'].lower() in fuel_release['name'].lower()):
                    test_config = ccf
                    break
    print('Testrail configuration: {}'.format(test_config['name']))

    # Get test suite
    rally_name = ' '.join([TestRailSettings.tests_suite,
                           TestRailSettings.tests_section])
    test_suite = project.get_suite_by_name(rally_name)
    test_section = project.get_section_by_name(suite_id=test_suite['id'],
                                               section_name=rally_name)

    # Get test cases for test section in suite
    test_cases = project.get_cases(
        suite_id=test_suite['id']
    )
    print('Testrail test suite "{}" contains {} test cases'.format(
        test_suite['name'], len(test_cases))
    )

    # Test plans have names like "<fuel-version> iso #<fuel-build>"
    test_plan_name = '{milestone} iso #{iso_number}'.format(
        milestone=milestone['name'],
        iso_number=fuel_version['build_number'])

    # Find appropriate test plan
    test_plan = project.get_plan_by_name(test_plan_name)
    if not test_plan:
        test_plan = project.add_plan(test_plan_name,
                                     description='http://jenkins-product.srt.'
                                     'mirantis.net:8080/job/{}.all/{}'.format(
                                         milestone['name'],
                                         fuel_version['build_number']
                                     ),
                                     milestone_id=milestone['id'],
                                     entries=[]
                                     )

    # Create test plan entry (run)
    plan_entries = []
    plan_entries.append(
        project.test_run_struct(
            name=JENKINS_JOB,
            suite_id=test_suite['id'],
            milestone_id=milestone['id'],
            description=cluster_description,
            config_ids=[test_config['id']]
        )
    )

    # Add newly created plan entry to test plan and renew plan on success
    if project.add_plan_entry(plan_id=test_plan['id'],
                              name=rally_name + ' - ' + JENKINS_JOB,
                              suite_id=test_suite['id'],
                              config_ids=[test_config['id']],
                              runs=plan_entries):
        test_plan = project.get_plan(test_plan['id'])

    # Find appropriate run
    for e in test_plan['entries']:
        for r in e['runs']:
            if(r['suite_id'] == test_suite['id']
                    and r['milestone_id'] == milestone['id']
                    and test_config['id'] in r['config_ids']):
                test_run = r
                break
                break

    print('Using Testrail run "{}" (ID {})'.format(
        test_run['name'],
        test_run['id']
    ))

    # Create list of test case names with ids for further use
    test_cases_exist = {}
    for tc in test_cases:
        test_cases_exist[tc['title']] = tc['id']

    # Will contain test results for publishing
    test_results = []

    # Will contain list of runned tests
    test_cases_run = []

    # Get Rally config
    CONF(sys.argv[1:], project='rally')

    # Prepare regexp for component matching
    re_comp = re.compile('([A-Z]+[a-z]+)')

    # It's may be more than one rally deployment on single cluster
    for deployment in rally_db.deployment_list(
        name=os.environ.get('SCALE_LAB_UUID')
    ):
        # Get all tasks for current cluster (which may have many deployments)
        for task in rally_db.task_list(deployment=deployment.uuid):

            try:
                (job, run, uuid) = task.tag.split('/')
            except ValueError:
                continue

            # Select tasks only for current job
            if(job == os.environ.get('JOB_NAME')
                    and run == os.environ.get('BUILD_NUMBER')):

                # Single task may have many scenarios
                for res in rally_db.task_result_get_all_by_uuid(task.uuid):

                    # Create test case if it is not exists
                    if res.key['name'] not in test_cases_exist.keys():
                        print('Create new test case: {}'.format(
                            res.key['name'])
                        )
                        # Get atomic actions as steps if any
                        if(len(res.data['raw']) > 0):
                            atomic_actions = [
                                {"content": aa, "expected": "pass"}
                                for aa in res.data['raw'][0]['atomic_actions']
                            ]
                        else:
                            atomic_actions = []
                        # Create test case object
                        test_case = {
                            'title': res.key['name'],
                            'type_id': 1,
                            'priority_id': project.get_default_priority('id'),
                            'custom_test_group':
                                re_comp.match(res.key['name']).group(1),
                            'custom_test_case_description': res.key['name'],
                            'custom_test_case_steps': atomic_actions
                        }
                        # Create test case in Testrail
                        new_test_case = project.add_case(
                            section_id=test_section['id'],
                            case=test_case
                        )

                        # Register test case as existing
                        test_cases.append(new_test_case)
                        test_cases_exist[res.key['name']] = new_test_case['id']

                    # Add test case to list of runned tests
                    test_cases_run.append(test_cases_exist[res.key['name']])

                    # Create test results
                    del test_results[:]
                    # To fail entire case last must be sent result with error
                    err_result = {}
                    for tr in res.data['raw']:
                        new_result = {
                            'case_id': test_cases_exist[res.key['name']],
                            'status_id': 1 if(len(tr['error']) == 0) else 5,
                            'elapsed': '{}s'.format(int(tr['duration']))
                            if(int(tr['duration']) > 0) else '0',
                            'version': fuel_version['build_number'],
                            'custom_test_case_steps_results': [{
                                'content': aa,
                                'expected': 'Any positive value (seconds)',
                                'actual':
                                    str(round(tr['atomic_actions'][aa], 3))
                                    if(tr['atomic_actions'][aa] > 0) else '0',
                                'status_id': 1
                                if(tr['atomic_actions'][aa] > 0) else 5
                            } for aa in tr['atomic_actions'].keys()]
                        }
                        # Rememer one result with error to send later
                        if(new_result['status_id'] != 1 and err_result == {}):
                            err_result = new_result
                        else:
                            test_results.append(new_result)
                        # Test results may be VERY HUGE so send it by chunks
                        if(len(test_results) >= 10000
                                and test_run):
                            print('Send results "{}"'.format(res.key['name']))
                            project.add_results_for_cases(
                                run_id=test_run['id'],
                                results=test_results
                            )
                            del test_results[:]
                    # Append erroneous result if any
                    if(err_result != {}):
                        test_results.append(err_result)
                    # Send unsent results
                    if(test_run and test_results):
                        print('Send results "{}"'.format(res.key['name']))
                        project.add_results_for_cases(
                            run_id=test_run['id'],
                            results=test_results
                        )


if __name__ == '__main__':
    main()
