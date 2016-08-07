Preparation
===========

1. pip install jenkins-job-builder
2. create file mos-scale.ini


[job_builder]
ignore_cache=True
keep_descriptions=False
recursive=False
allow_duplicates=False

[jenkins]
user=mirantis_login
password=mirantis_password
url=http://mos-scale.vm.mirantis.net:8080/



Usage
=====

Testing
-------
Execute
jenkins-jobs --conf mos-scale.ini test mos-scale/jenkins_job_builder/1_lab_mirantis

You should see valid XML code without errors

Deploy
------
Execute
jenkins-jobs --conf mos-scale.ini update mos-scale/jenkins_job_builder/1_lab_mirantis
