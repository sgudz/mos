#!/bin/bash -xe

TOP_DIR=$(cd $(dirname "$0") && pwd)
USER_NAME=${USER_NAME:-developer}
USER_HOME=${USER_HOME:-/home/${USER_NAME}}
DEST=${DEST:-/opt/stack}
VIRTUALENV_DIR=${VIRTUALENV_DIR:-${DEST}/.venv}

install_helpers() {
    echo "Installing tempest helpers"
    cp ${TOP_DIR}/helpers/subunit-shouldfail-filter.py ${VIRTUALENV_DIR}/bin/subunit-shouldfail-filter
    cp ${TOP_DIR}/helpers/subunit2html.py ${VIRTUALENV_DIR}/bin/subunit2html
    cp ${TOP_DIR}/helpers/colorizer.py ${VIRTUALENV_DIR}/bin/colorizer
}

install_tempest() {
    echo "Installing Tempest into ${DEST}"
    cd ${DEST}
    TEMPEST_DIR="${DEST}/tempest"
    rm -rf ${TEMPEST_DIR}
    git clone git://git.openstack.org/openstack/tempest.git
    cd ${TEMPEST_DIR}
    ${VIRTUALENV_DIR}/bin/python setup.py install
    # TODO (ylobankov): don't use the workaround when bug #1410622 is fixed.
    # This is the workaround to avoid failures for EC2 tests. According to
    # the bug #1408987 reported to Nova these tests permanently fail since
    # the boto 2.35.0 has been released. The bug #1408987 was fixed and
    # backported to the Juno release. However the issue has not been completely
    # resolved. The corresponding bug #1410622 was reported to Nova and was
    # fixed only for Kilo.
    ${VIRTUALENV_DIR}/bin/pip install boto==2.34.0
    mkdir -p /etc/tempest
    chmod -R o+w /etc/tempest
    cp ${TOP_DIR}/helpers/tempest.sh ${VIRTUALENV_DIR}/bin/tempest
    cp -r ${TOP_DIR}/tempest-options ${DEST}/
    echo "Tempest installed into ${TEMPEST_DIR}"

    echo "Downloading necessary resources"
    TEMPEST_FILES="${VIRTUALENV_DIR}/files"
    rm -rf ${TEMPEST_FILES}
    mkdir ${TEMPEST_FILES}

    CIRROS_VERSION=${CIRROS_VERSION:-"0.3.2"}
    CIRROS_IMAGE_URL="http://download.cirros-cloud.net/${CIRROS_VERSION}/cirros-${CIRROS_VERSION}-x86_64-uec.tar.gz"
    wget -O ${TEMPEST_FILES}/cirros-${CIRROS_VERSION}-x86_64-uec.tar.gz ${CIRROS_IMAGE_URL}
    cd ${TEMPEST_FILES}
    tar xzf cirros-${CIRROS_VERSION}-x86_64-uec.tar.gz
}

main() {
    cd ${TOP_DIR}
    install_helpers
    install_tempest
    cd -
}

main "$@"