from flask import Flask
import os
import database
from database import JobInfoRecord
from flask import render_template
from flask import request
from datetime import datetime
from sqlalchemy import and_


HTML_TEMPLATE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "templates")
HTML_TEMPLATE = "report.html"
HTML_TEMPLATE_NO_FILTER = "report_no_filter.html"
JOB_RESULTS_TBL_HTML_TEMPLATE = "job_results_table.html"
OUTPUT_HTML_REPORT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "index.html")
TBL_JOBS_HTML = "job_results_table.html"
OPTIONS_HTML = "index.html"

app = Flask(__name__, template_folder=HTML_TEMPLATE_DIR)


@app.route("/")
def show_options():
    return render_template(OPTIONS_HTML)


def get_filter(only_fuel_jobs=False):
    if request.form['env'] != "" and request.form['date_start'] != ""\
            and request.form['date_end'] != ""\
            and request.form['contact_person'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))

    elif request.form['env'] != "" and request.form['date_start'] != ""\
            and request.form['date_end'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")
        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date)
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date)
    elif request.form['contact_person'] != ""\
            and request.form['date_start'] != ""\
            and request.form['date_end'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
    elif request.form['env'] != "" and request.form['date_start'] != ""\
            and request.form['contact_person'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
    elif request.form['env'] != "" and request.form['date_end'] != ""\
            and request.form['contact_person'] != "":
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started <= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started <= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
    elif request.form['env'] != "" and request.form['date_start'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date)
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started >= start_date)
    elif request.form['env'] != "" and request.form['date_end'] != "":
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started <= end_date)
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.started <= end_date)
    elif request.form['env'] != "" and request.form['contact_person'] != "":
        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.env.
                              __eq__(request.form['env']),
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
    elif request.form['date_start'] != "" and request.form['date_end'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date)
        else:
            filter_exp = and_(JobInfoRecord.started >= start_date,
                              JobInfoRecord.started <= end_date)
    elif request.form['date_start'] != ""\
            and request.form['contact_person'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.started >= start_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.started >= start_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
    elif request.form['date_end'] != ""\
            and request.form['contact_person'] != "":
        end_date = datetime.strptime(request.form['date_start'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.started >= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = and_(JobInfoRecord.started >= end_date,
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
    elif request.form['env'] != "":

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.env.
                              __eq__(request.form['env']))
        else:
            filter_exp = JobInfoRecord.env.__eq__(request.form['env'])
    elif request.form['date_start'] != "":
        start_date = datetime.strptime(request.form['date_start'],
                                       "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.started >= start_date)
        else:
            filter_exp = JobInfoRecord.started >= start_date
    elif request.form['date_end'] != "":
        end_date = datetime.strptime(request.form['date_end'],
                                     "%Y-%m-%dT%H:%M")

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.ended >= end_date)
        else:
            filter_exp = JobInfoRecord.ended >= end_date
    elif request.form['contact_person'] != "":

        if only_fuel_jobs:
            filter_exp = and_(JobInfoRecord.job_name.
                              like('%env-deploy-fuel'),
                              JobInfoRecord.contact_person.
                              __eq__(request.form['contact_person']))
        else:
            filter_exp = JobInfoRecord.contact_person.\
                __eq__(request.form['contact_person'])

    return filter_exp


@app.route("/all_jobs/", methods=['GET', 'POST'])
def all_jobs():
    filter_exp = None
    if request.method == 'POST':
        if request.form['action'] == "Submit":
            res = database.update_job_record(
                record_id=request.form['record_id'],
                bug_id=request.form['bug_id'],
                description=request.form['description'],
                contact_person=request.form['contact_person'],
                job_settings=request.form['job_settings'],
                log_snapshot=request.form['log_snapshot'])
            if not res:
                return "Failed to save changes for record!"
        elif request.form['action'] == "Filter":
            filter_exp = get_filter()
        else:
            return "Unknown action %s received on POST request!",\
                request.form['action']

    res = database.get_all_records_from_table(JobInfoRecord, filter_exp,
                                              JobInfoRecord.started.desc())
    return render_template(HTML_TEMPLATE, records=res,
                           executors_results_template=TBL_JOBS_HTML)


@app.route("/fuel_jobs/", methods=['GET', 'POST'])
def fuel_jobs():
    filter_exp = JobInfoRecord.job_name.like('%env-deploy-fuel')
    if request.method == 'POST':
        if request.form['action'] == "Submit":
            res = database.update_job_record(
                record_id=request.form['record_id'],
                bug_id=request.form['bug_id'],
                description=request.form['description'],
                contact_person=request.form['contact_person'],
                job_settings=request.form['job_settings'],
                log_snapshot=request.form['log_snapshot'])
            if not res:
                return "Failed to save changes for record!"
        elif request.form['action'] == "Filter":
            filter_exp = get_filter(True)
        else:
            return "Unknown action %s received on POST request!",\
                   request.form['action']
    res = database.get_all_records_from_table(JobInfoRecord, filter_exp,
                                              JobInfoRecord.started.desc())
    if len(res) == 0:
        return "No Fuel jobs found!"
    return render_template(HTML_TEMPLATE, records=res,
                           executors_results_template=TBL_JOBS_HTML)


@app.route('/show_child/<int:parent_id>/', methods=['GET', 'POST'])
def show_child(parent_id):
    if request.method == 'POST':
        if request.form['action'] == "Submit":
            res = database.update_job_record(
                record_id=request.form['record_id'],
                bug_id=request.form['bug_id'],
                description=request.form['description'],
                contact_person=request.form['contact_person'],
                job_settings=request.form['job_settings'],
                log_snapshot=request.form['log_snapshot'])
            if not res:
                return "Failed to save changes for record!"
        else:
            return "Unknown action %s received on POST request!",\
                   request.form['action']

    res = database.get_all_records_from_table(JobInfoRecord,
                                              JobInfoRecord.parent_job_id.
                                              __eq__(str(parent_id)),
                                              JobInfoRecord.started.desc())
    if len(res) == 0:
        return "Job with id: \'" + str(parent_id) + "\' has no child jobs!"
    return render_template(HTML_TEMPLATE_NO_FILTER, records=res,
                           executors_results_template=TBL_JOBS_HTML)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=6003, debug=True)
