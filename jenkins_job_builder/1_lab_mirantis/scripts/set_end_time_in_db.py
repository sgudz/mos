#!/usr/bin/python
import sys
import os
import datetime
sys.path.append('/var/www/reporting/reporting/')
import database
import subprocess
import re
from database import JobInfoRecord

REPORT_DIR = '/var/www/test_results'


def find_dir(name_part, path):
    name = "jenkins-" + name_part + "*"
    try:
        ret = subprocess.check_output(['find', path, '-name', name])
    except Exception:
        return ""
    return ret

record_id = os.environ.get('DB_RECORD_ID')
database.update_column_record_in_table(JobInfoRecord,
                                       JobInfoRecord.id.__eq__(record_id),
                                       'ended', datetime.datetime.now())
uuid = os.environ.get('JOB_NAME') + '-' + os.environ.get('BUILD_NUMBER')

if re.match(r'.*rally.*', uuid) or\
        re.match(r'.*shaker.*', uuid):
    report_path = find_dir(uuid, REPORT_DIR)
    if report_path != "":
        report_path = report_path.split(REPORT_DIR)[-1]
        database.update_column_record_in_table(JobInfoRecord,
                                               JobInfoRecord.id.
                                               __eq__(record_id),
                                               'report_dir', report_path)
