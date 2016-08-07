#!/bin/bash -xe

TOP_DIR=$(cd $(dirname "$0") && pwd)
USER_NAME=${USER_NAME:-developer}
USER_HOME=${USER_HOME:-/home/${USER_NAME}}
DEST=${DEST:-/opt/stack}
VIRTUALENV_DIR=${VIRTUALENV_DIR:-${DEST}/.venv}

install_helpers() {
    echo "Installing ceilometer helpers"
    cp ${TOP_DIR}/helpers/functions_ceilometer.sh ${VIRTUALENV_DIR}/bin/
    cp ${TOP_DIR}/helpers/mongo_io_script.py ${VIRTUALENV_DIR}/bin/mongo_io_script
    cp ${TOP_DIR}/helpers/run-ceilo-test.sh ${VIRTUALENV_DIR}/bin/run-ceilo-test
    cp ${TOP_DIR}/helpers/ceilometer_log_collector.py ${VIRTUALENV_DIR}/bin/ceilometer_log_collector
    cp -r ${TOP_DIR}/helpers/templates ${DEST}/
}

main() {
    cd ${TOP_DIR}
    install_helpers
    cd -
}

main "$@"