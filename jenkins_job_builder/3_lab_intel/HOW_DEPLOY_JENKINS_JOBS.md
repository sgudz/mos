Preparation
===========

1. pip install jenkins-job-builder
2. create file mos-scale-3.ini


[job_builder]
ignore_cache=True
keep_descriptions=False
recursive=False
allow_duplicates=False

[jenkins]
user=sgalkin
password=sgalkin123
url=http://10.3.60.51:8080/



Usage
=====

Testing
-------
Execute
jenkins-jobs --conf mos-scale-3.ini test mos-scale/jenkins_job_builder/3_lab_intel

You should see valid XML code without errors

Deploy
------
Execute
jenkins-jobs --conf mos-scale-3.ini update mos-scale/jenkins_job_builder/3_lab_intel
