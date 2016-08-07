#!/bin/bash

# Check in what place we have rally
if [ `which rally` ]; then
    RALLY=`which rally`
elif [ -f "virtualenv/bin/rally" ]; then
    RALLY="virtualenv/bin/rally"
else
   echo "Rally not found!"
fi

cd ${SCENARIOS_DIR}
SCENARIOS=`find ${SCENARIOS_NAMES} \( -name "*.json" -or -name "*.yaml" \) | uniq`
cd -

if (( $? != 0 )); then
    echo "ERROR: Can't find scenarios, check again!!!"
fi

for SCENARIO in ${SCENARIOS}; do
    BASENAME=$(basename -s .json -s .yaml ${SCENARIO})
    LOG=${BASENAME}.log

    echo ${BASENAME}

    ${RALLY} --debug --noverbose --log-dir ${ARTIFACTS_DIR} --log-file $LOG \
        --plugin-paths ${PLUGINS_PATH} \
        task start --tag ${BASENAME} --task-args-file ${JOB_PARAMS_CONFIG} \
        ${SCENARIOS_DIR}/$SCENARIO 2>&1 | tee ${ARTIFACTS_DIR}/rally.log | grep -Ew "ITER|ERROR" || true

    # Enable export to influxdb/grafana
    if [ ${NEED_EXPORT_RESULT} ]; then
        # don't use `task --uuid-only` in 0.4.0 this list is not sorted
        # "sed -e '$ d'" removes last blank line
        LAST_RALLY_TASK=`${RALLY} task list | awk -F"|" '{print $2}' | sed s/" "//g | sed -e '$ d' | tail -1`
        ${RALLY} --plugin-paths ${PLUGINS_PATH} task export --uuid ${LAST_RALLY_TASK} --connection ${INFLUXDB_CONNECTION}
    fi
done
