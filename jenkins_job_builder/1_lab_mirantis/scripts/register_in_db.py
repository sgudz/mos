#!/usr/bin/python
import os
import sys
sys.path.append('/var/www/reporting/reporting/')
import database
import datetime

parent_id = None
job_settings = None
if os.environ.get('JOB_NAME').endswith("deploy-fuel"):
    job_settings = os.environ.get('ISO_CUSTOM_URL')
elif os.environ.get('JOB_NAME').endswith("deploy-cluster"):
    parent_id = database.get_job_id_from_env_status('{env}', True)
    job_settings = os.environ.get('MAIN_OS') + '+'
    job_settings += os.environ.get('PROVISION_METHOD') + '+'
    job_settings += os.environ.get('SEGMENTATION_TYPE') + '\n'
    job_settings += "Controllers: " + os.environ.get('CONTROLLER_COUNT')
    job_settings += " Computes :" + os.environ.get('COMPUTE_COUNT')
    job_settings += " Ceph nodes :" + os.environ.get('CEPH_COUNT') + '\n'
    job_settings += "Settings: "
    job_settings += "Murano, " if os.environ.get('MURANO') == "true" else ""
    job_settings += "Sahara, " if os.environ.get('SAHARA') == "true" else ""
    job_settings += "Ceilometer, " if os.environ.get('CEILOMETER') == "\
        true" else ""
    job_settings += "Volumes LVM, " if os.environ.get('VOLUMES_LVM') == "\
        true" else ""
    job_settings += "Volumes Ceph, " if os.environ.get('VOLUMES_CEPH') == "\
        true" else ""
    job_settings += "Images Ceph, " if os.environ.get('IMAGES_CEPH') == "\
        true" else ""
    job_settings += "Ephemeral Ceph, "\
        if os.environ.get('EPHEMERAL_CEPH') == "\
        true" else ""
    job_settings += "Objects Ceph, " if os.environ.get('OBJECTS_CEPH') == "\
        true" else ""
    job_settings += "Debug, " if os.environ.get('DEBUG') == "true" else ""
    job_settings += "Nova quota, " if os.environ.get('NOVA_QUOTA') == "\
        true" else ""
    job_settings += "Network verification, "\
        if os.environ.get('NETWORK_VERIFICATION') == "\
        true" else ""
    job_settings += "LMA, " if os.environ.get('LMA') == "\
        true" else ""
    job_settings += "Power on delay: " + os.environ.get('POWER_ON_DELAY')
else:
    parent_id = database.get_job_id_from_env_status('{env}')


cur_id = database.add_job_record(uuid=os.environ.get('JOB_NAME') + '-' +
                                 os.environ.get('BUILD_NUMBER'),
                                 started=datetime.datetime.now(),
                                 job_name=os.environ.get('JOB_NAME'),
                                 contact_person=os.environ.get('BUILD_USER'),
                                 parent_job_id=parent_id, env='{env}',
                                 description=os.environ.get(
                                     'BUILD_DESCRIPTION'),
                                 bug_id=os.environ.get('BUG_ID'),
                                 job_settings=job_settings,
                                 job_type=os.environ.get('EXECUTION_TYPE'))

if os.environ.get('JOB_NAME').endswith("deploy-fuel"):
    database.update_env_status('{env}', cur_id, True)
elif os.environ.get('JOB_NAME').endswith("deploy-cluster"):
    database.update_env_status('{env}', cur_id)

f = open(os.environ.get('WORKSPACE') + '/build.properties', 'w+')
f.write('DB_RECORD_ID=' + str(cur_id))
f.close()
