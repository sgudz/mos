#!/bin/bash -xe

TOP_DIR=$(cd $(dirname "$0") && pwd)
USER_NAME=${USER_NAME:-developer}
USER_HOME=${USER_HOME:-/home/${USER_NAME}}
DEST=${DEST:-/opt/stack}
VIRTUALENV_DIR=${VIRTUALENV_DIR:-${DEST}/.venv}

install_shaker() {
    echo "Installing Shaker"
    cd ${DEST}
    rm -rf shaker
    git clone git://git.openstack.org/openstack/shaker
    cd shaker
    mkdir -p /etc/shaker
    cat etc/shaker.conf | \
        sed 's|#server_endpoint\b.*|server_endpoint='${FUEL_IP}:5999'|' | \
        sed 's|#log_file\b.*|log_file=/var/log/job-reports/shaker.log|' | \
        sed 's|#debug\b.*|debug=True|' > /etc/shaker/shaker.conf

    ${VIRTUALENV_DIR}/bin/python setup.py install
    # Install requirements
    source ${VIRTUALENV_DIR}/bin/activate
    pip2.7 install -r ./requirements.txt
    deactivate
    # copy Shaker scenarios into /opt/stack
    cp -r ${TOP_DIR}/../../../mos-scenarios/shaker-scenarios ${DEST}/
    iptables -I INPUT 1 -p tcp --dport 5999 -j ACCEPT
}

main() {
    cd ${TOP_DIR}
    install_shaker
    cd
}

main "$@"

