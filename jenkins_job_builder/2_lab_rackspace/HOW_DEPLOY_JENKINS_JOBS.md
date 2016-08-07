Preparation
===========

1. pip install jenkins-job-builder
2. create file mos-scale-2.ini


[job_builder]
ignore_cache=True
keep_descriptions=False
recursive=False
allow_duplicates=False

[jenkins]
url=http://172.20.8.32:8080/



Usage
=====

Testing
-------
Execute
jenkins-jobs --conf mos-scale-2.ini test mos-scale/jenkins_job_builder/2_lab_rackspace

You should see valid XML code without errors

Deploy
------
Execute
jenkins-jobs --conf mos-scale-2.ini update mos-scale/jenkins_job_builder/2_lab_rackspace
