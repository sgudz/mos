#!/bin/bash

rarse_args() {

    TOP_DIR=$(cd $(dirname "$0") && pwd)
    DEST=${DEST:-/opt/stack}
    FILE=${DEST}/other-rally-scenarios/ceilometer-perfomance/nova/boot-and-delete_server.yaml

    while [[ $# > 0 ]]; do
        key="$1"
        shift

        case $key in
            -c|compute|--compute)
            COMPUTE="$1"
            shift
            ;;
            -r|concurrency|--concurrency)
            CONCURRENCY="$1"
            shift
            ;;
            -d|cidr|network|--cidr|--network)
            CIDR="$1"
            shift
            ;;
            -n|net_per_tenant|--net_per_tenant)
            NET_PER_TENANT="$1"
            shift
            ;;
            -u|users|users_per_tenant|--users|--users_per_tenant)
            USERS_PER_TENANT="$1"
            shift
            ;;
            -s|sleep|--sleep)
            SLEEP="$1"
            shift
            ;;
            -o|timeout|--timeout)
            TIMEOUT="$1"
            shift
            ;;
            -t|tenants|--tenants)
            TENANTS="$1"
            shift
            ;;
            -h|help|--help)
            echo "
arguments:
-c|compute|--compute
-r|concurrency|--concurrency
-d|cidr|network|--cidr|--network
-n|net_per_tenant|--net_per_tenant
-u|users|users_per_tenant|--users|--users_per_tenant
-t|tenants|--tenants
-h|help|--help
-s|sleep|--sleep
-o|timeout|--timeout

yaml for generate:"
            cat ${FILE}.sample
            echo
            exit
            ;;
            *)
            echo "$1 is unknown option"
            exit 1
            ;;
        esac
    done

    COMPUTE=${COMPUTE:-10}
    CONCURRENCY=${CONCURRENCY:-2}
    CIDR=${CIDR:-"10.100.0.0/24"}
    NET_PER_TENANT=${NET_PER_TENANT:-1}
    USERS_PER_TENANT=${USERS_PER_TENANT:-1}
    TENANTS=${TENANTS:-$((2+$(($COMPUTE/20))))}
    RUNNER_TYPE=${RUNNER_TYPE:-"rps"}
    SLEEP=${SLEEP:-300}
    TIMEOUT=${TIMEOUT:-600}
}

rarse_args $@

cp ${FILE}.sample ${FILE}

GLOBAL_TIMEOUT=$(echo ${COMPUTE}/${CONCURRENCY} | bc -l | awk -F. '{print $1}')
if [ -z "${GLOBAL_TIMEOUT}" ]; then
    GLOBAL_TIMEOUT=600;
else
    GLOBAL_TIMEOUT=$[$GLOBAL_TIMEOUT+600]
fi

sed -i "s/{{ sleep }}/${SLEEP}/" ${FILE}
sed -i "s/{{ timeout }}/${TIMEOUT}/" ${FILE}
sed -i "s/{{ tenants }}/${TENANTS}/" ${FILE}
sed -i "s/{{ users_per_tenant }}/${USERS_PER_TENANT}/" ${FILE}
sed -i "s/{{ cidr }}/${CIDR}/" ${FILE}
sed -i "s/{{ net_per_tenant }}/${NET_PER_TENANT}/" ${FILE}

source ${TOP_DIR}/functions_ceilometer.sh

run_ceilometer_logs

export GLOBAL_TIMEOUT=${GLOBAL_TIMEOUT}
export  CONCURRENCY=${CONCURRENCY}
export COMPUTE=${COMPUTE}

run_rally --task ${FILE}

rm ${FILE}
stop_ceilometer_logs

if [ `ls /tmp/ceilometer_logs/ | wc -l` -ne 0 ]; then
    python $DEST/.venv/bin/ceilometer_log_collector -t $DEST/templates/ceilometer-results.mako
fi