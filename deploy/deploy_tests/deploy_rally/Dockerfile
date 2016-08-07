FROM ubuntu:14.04

# Default rally DB connection string. Set global to image.
# Can be:
# for Mysql - mysql+pymysql://user:pass@localhost/dbname
# for sqlite - sqlite:////tmp/rally.sqlite
# for postgres - postgres://user:pass@localhost/dbname
ARG DB_CONNECTION

# Base dir
ENV BASE_DIR /data/rally

# Path to plugin for rally
ENV PLUGINS_PATH rally_plugins

# Name of the deployment
ENV DEPLOYMENT_NAME default_deployment

# Rally config for create deployement
ENV DEPLOYMENT_CONFIG deployment.json

# Directory with scenarios in container
ENV SCENARIOS_DIR mos_scenarios

# Which scenarios need to run.
# Path relatively to SCENARIOS_PATH with scenario files
# Can be: string of dir and files separated by space.
ENV SCENARIOS_NAMES rally-scenarios

# Config file for rally task start
ENV JOB_PARAMS_CONFIG job-params.yaml

# Specifies whether to export data in influxdb/grafana
ENV NEED_EXPORT_RESULT yes

# Influxdb connection string for export data plugin from rally
# to influxdb/grafana
ENV INFLUXDB_CONNECTION influxdb://user:pass@localhost:8086/dbname

# Specify artifacts dir for runtime generated data (logs, process results, etc)
ENV ARTIFACTS_DIR $BASE_DIR/artifacts


RUN apt-get update && \
    apt-get install -y python build-essential libssl-dev python-distribute \
    libffi-dev python-dev libxml2-dev libxslt1-dev libpq-dev git && \
    easy_install virtualenv

# Build project
RUN mkdir -p $BASE_DIR && mkdir -p $ARTIFACTS_DIR
ADD ./deploy_rally ./requirements.txt ./Makefile $BASE_DIR/
ADD ./bin $BASE_DIR/bin

WORKDIR $BASE_DIR
RUN virtualenv virtualenv && . virtualenv/bin/activate && \
    pip install -r requirements.txt

ADD ./rally.conf $BASE_DIR/virtualenv/etc/rally/rally.conf

RUN sed -i "s|connection *=.*|connection = ${DB_CONNECTION}|" \
    $BASE_DIR/virtualenv/etc/rally/rally.conf

# Clean up APT when done.
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

VOLUME [$ARTIFACTS_DIR]
CMD ["make", "test"]
