#!/bin/bash

JOB_REPORTS_DIR=/var/log/job-reports

TOP_DIR=$(cd $(dirname "$0") && pwd)
DEST=${DEST:-/opt/stack}
SERIAL=${SERIAL:-0}

source ${TOP_DIR}/functions.sh

SHOULDFAIL_FILE="${DEST}/tempest-options/shouldfail.yaml"
FUEL_RELEASE=`echo ${FUEL_RELEASE} | sed 's/\./_/g'`
if [ -f ${DEST}/tempest-options/shouldfail_${FUEL_RELEASE}.yaml ]; then
    SHOULDFAIL_FILE="${DEST}/tempest-options/shouldfail_${FUEL_RELEASE}.yaml"
fi

print_usage() {
    echo "This script configures and runs Tempest"
    echo "Usage: ${0##*/} [-d|h] "
    echo "Options:"
    echo "  -h:                prints this help message"
    echo "  -d:                switch debug logs on"
    echo "  [TESTROPTIONS]     Arguments are passed to testr"
}

error() {
    printf "\e[31mError: %s\e[0m\n" "${*}" >&2
    exit 1
}

message() {
    printf "\e[33m%s\e[0m\n" "${1}"
}

parse_arguments() {
    DEBUG="false"

    while getopts ":hd" opt; do
        case ${opt} in
            h)
                print_usage
                exit 0
                ;;
            d)
                DEBUG="true"
                ;;
            *)
                error "An invalid option has been detected."
                print_usage
                exit 1
        esac
    done
    shift $((OPTIND-1))
    [ "$1" = "--" ] && shift
    TESTARGS="$@"
}

check_service_availability() {
    SVC="`keystone service-list | grep $1 | wc -l`"
    if [ "${SVC}" -eq "0" ]; then
        echo "false"
    else
        echo "true"
    fi
}

prepare() {
    message "Save execution settions"
    echo "{'type': '${EXECUTION_TYPE:-scale}'}" > ${DEST}/executor_settings.json
    message "Configuring Tempest"

    NEUTRON_AVAILABLE=$(check_service_availability "neutron")
    NOVA_AVAILABLE=$(check_service_availability "nova")
    CINDER_AVAILABLE=$(check_service_availability "cinder")
    GLANCE_AVAILABLE=$(check_service_availability "glance")
    SWIFT_AVAILABLE=$(check_service_availability "swift")
    HEAT_AVAILABLE=$(check_service_availability "heat")
    CEILOMETER_AVAILABLE=$(check_service_availability "ceilometer")
    SAHARA_AVAILABLE=$(check_service_availability "sahara")

    if [ "${NEUTRON_AVAILABLE}" == "true" ]; then
        PUBLIC_NETWORK_ID="`neutron net-list --router:external=True -f csv -c id --quote none | tail -1`"
        PUBLIC_ROUTER_ID="`neutron router-list --external_gateway_info:network_id=${PUBLIC_NETWORK_ID} -F id -f csv --quote none | tail -1`"
    fi
    IMAGE_REF="`glance image-list --name TestVM | grep TestVM | awk '{print $2}'`"

    TEMPEST_CONF="`mktemp`"

    cat > ${TEMPEST_CONF} << EOF
[DEFAULT]
debug = ${DEBUG}
use_stderr = false
lock_path = /tmp
log_file = tempest.log

[boto]
ec2_url = ${OS_EC2_URL}

[cli]
cli_dir = ${DEST}/.venv/bin
has_manage = false

[compute]
image_ref = ${IMAGE_REF}
image_ref_alt = ${IMAGE_REF}
flavor_ref = 0
flavor_ref_alt = 42
ssh_user = cirros
image_ssh_user = cirros
image_alt_ssh_user = cirros
fixed_network_name=net04
network_for_ssh=net04_ext
build_timeout = 300
allow_tenant_isolation = True

[compute-feature-enabled]
live_migration = false
resize = True
vnc_console = true

[dashboard]
login_url = ${OS_DASHBOARD_URL}auth/login/
dashboard_url = ${OS_DASHBOARD_URL}project/

[identity]
admin_password = ${OS_PASSWORD}
admin_tenant_name = ${OS_TENANT_NAME}
admin_username = ${OS_USERNAME}
admin_domain_name = Default
password = demo
tenant_name = demo
username = demo
uri = ${OS_AUTH_URL}
uri_v3 = ${OS_AUTH_URL_V3}

[network]
public_network_id = ${PUBLIC_NETWORK_ID}

[network-feature-enabled]
api_extensions = ext-gw-mode,security-group,l3_agent_scheduler,binding,quotas,dhcp_agent_scheduler,multi-provider,agent,external-net,router,metering,allowed-address-pairs,extra_dhcp_opt,extraroute

[object-storage]
operator_role = SwiftOperator

[scenario]
img_dir = ${DEST}/.venv/files
ami_img_file = cirros-0.3.2-x86_64-blank.img
ari_img_file = cirros-0.3.2-x86_64-initrd
aki_img_file = cirros-0.3.2-x86_64-vmlinuz
large_ops_number = 10

[service_available]
neutron = ${NEUTRON_AVAILABLE}
nova = ${NOVA_AVAILABLE}
cinder = ${CINDER_AVAILABLE}
glance = ${GLANCE_AVAILABLE}
swift = ${SWIFT_AVAILABLE}
heat = ${HEAT_AVAILABLE}
ceilometer = ${CEILOMETER_AVAILABLE}
sahara = ${SAHARA_AVAILABLE}
ironic = false
trove = false
marconi = false

[volume]
build_timeout = 300

[volume-feature-enabled]
backup = false
EOF

    config_file=`readlink -f "${TEMPEST_CONF}"`
    export TEMPEST_CONFIG_DIR=`dirname "${TEMPEST_CONF}"`
    export TEMPEST_CONFIG=`basename "${TEMPEST_CONF}"`
    message "Tempest config:"
    cat ${TEMPEST_CONF} > ${JOB_REPORTS_DIR}/tempest.conf
    cat ${TEMPEST_CONF}
    message "Shouldfail:"
    cat ${SHOULDFAIL_FILE} > ${JOB_REPORTS_DIR}/shouldfail.yaml
    cat ${SHOULDFAIL_FILE}
}

function testr_init {
    if [ ! -d .testrepository ]; then
        testr init
    fi
}

function run_tests {
    testr_init
    find . -type f -name "*.pyc" -delete
    export OS_TEST_PATH=./tempest/test_discover

    if [ "${DEBUG}" = "true" ]; then
        if [ "${TESTARGS}" = "" ]; then
            TESTARGS="discover ./tempest/test_discover"
        fi
        python -m testtools.run ${TESTARGS}
        return $?
    fi

    SUBUNIT_STREAM=`cat .testrepository/next-stream`
    TESTR_PARAMS=""

    if [ ${SERIAL} -eq 0 ]; then
        TESTR_PARAMS="--parallel"
    fi

    testr run ${TESTR_PARAMS} --subunit ${TESTARGS} | subunit-1to2 | ${TOP_DIR}/subunit-shouldfail-filter --shouldfail-file=${SHOULDFAIL_FILE} | subunit-2to1 | ${TOP_DIR}/colorizer

    if [ -f ".testrepository/${SUBUNIT_STREAM}" ] ; then
        SUBUNIT="`mktemp`"
        subunit-1to2 < .testrepository/${SUBUNIT_STREAM} | ${TOP_DIR}/subunit-shouldfail-filter --shouldfail-file=${SHOULDFAIL_FILE} > ${SUBUNIT}
        ${TOP_DIR}/subunit2html < ${SUBUNIT} > ${JOB_REPORTS_DIR}/tempest-report.html
        subunit2junitxml < ${SUBUNIT} > ${JOB_REPORTS_DIR}/tempest-report.xml
    else
        error "Subunit stream ${SUBUNIT_STREAM} is not found"
    fi
}

run() {
    message "Running Tempest"

    cd /opt/stack/tempest/
    run_tests
    cd ${TOP_DIR}
}

main() {
    parse_arguments "$@"
    prepare
    run "$@"
}

main "$@"
