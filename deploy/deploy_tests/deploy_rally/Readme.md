# Build docker image
```
docker build --build-arg DB_CONNECTION="postgres://user:pass@localhost/dbname" -t rally .
```

# Create container
If you need different connection for rally, you must set DB_CONNECTION env.
```
docker run -e DEPLOYMENT_NAME=test_name -e INFLUXDB_CONNECTION=influxdb://user:pass@host/dbname rally \
-v deployment.json:/data/rally/deployment.json -v rally_scenarios:/data/rally/rally_scenarios \
-v job-params.yaml:/data/rally/job-params.yaml
```

# Config env

default working dir /data/rally

* PLUGINS_PATH - Path to plugin for rally (defult: rally_plugins)
* DEPLOYMENT_NAME - Name of the deployment (defult: default_deployment)
* DEPLOYMENT_CONFIG - Rally config for create deployement (defult: deployment.json)
* SCENARIOS_PATH - Path with single or dir scenarios (defult: rally_scenarios)
* JOB_PARAMS_CONFIG - Config file for rally task start (defult: job-params.yaml)
* NEED_EXPORT_RESULT - Specifies whether to export data in influxdb/grafana (defult: yes)
* INFLUXDB_CONNECTION - Influxdb connection string for export data plugin
                        from rally to influxdb/grafana (defult: influxdb://user:pass@host:port/dbname)
