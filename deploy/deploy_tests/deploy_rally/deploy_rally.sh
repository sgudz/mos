#!/bin/bash -xe

TOP_DIR=$(cd $(dirname "$0")/deploy_rally && pwd)
USER_NAME=${USER_NAME:-developer}
USER_HOME=${USER_HOME:-/home/${USER_NAME}}
DEST=${DEST:-/opt/stack}
VIRTUALENV_DIR=${VIRTUALENV_DIR:-${DEST}/.venv}
RALLY_VERSION=${RALLY_VERSION:-last_stable}
SCALE_LAB_UUID=${SCALE_LAB_UUID}
SAHARA_IMAGE_NAME="SaharaVanilla"
SAHARA_IMAGE_URL="http://sahara-files.mirantis.com/images/upstream/liberty/sahara-liberty-vanilla-2.7.1-ubuntu-14.04.qcow2"

install_rally() {
    echo  "Installing Rally into ${DEST}"
    cd ${DEST}
    RALLY_DIR=${DEST}/rally
    rm -rf ${RALLY_DIR}
    git clone git://git.openstack.org/openstack/rally.git
    cd ${RALLY_DIR}
    test "${RALLY_VERSION}" = "last_stable" && RALLY_VERSION=$(git tag -l [0-9].[0-9].[0-9] | sort -n | tail -1)
    if [ -n "${RALLY_VERSION}" ]
    then
        git checkout ${RALLY_VERSION}
    fi
    ${VIRTUALENV_DIR}/bin/pip install pbr==0.10.3
    ${VIRTUALENV_DIR}/bin/pip install -r requirements.txt
    ${VIRTUALENV_DIR}/bin/pip install oslo.i18n --upgrade
    ${VIRTUALENV_DIR}/bin/python setup.py install
    echo "Rally installed into ${RALLY_DIR}"

    if [ -n "${USE_PROXY}" ]; then
        CONTROLLER_HOST_ID="`fuel node | grep controller | awk '{print $1}' | head -1`"
        CONTROLLER_HOST="node-${CONTROLLER_HOST_ID}"
        export HTTP_PROXY=http://${CONTROLLER_HOST}:8888
        export HTTPS_PROXY=http://${CONTROLLER_HOST}:8888
    fi
}

install_helpers() {
    echo "Installing rally helpers"
    cp -r ${TOP_DIR}/helpers/etc ${VIRTUALENV_DIR}/
    cp ${TOP_DIR}/helpers/run_rally.py ${VIRTUALENV_DIR}/bin/run_rally
    cp ${TOP_DIR}/helpers/rally_cleanup.py ${VIRTUALENV_DIR}/bin/rally_cleanup
    cp ${TOP_DIR}/helpers/shaker_prepare_and_loop.sh ${VIRTUALENV_DIR}/bin/shaker_prepare_and_loop
}

configure_rally() {
    echo "Configuring Rally"

    RALLY_CONFIGURATION_DIR="/etc/rally"
    RALLY_DATABASE_DIR="${VIRTUALENV_DIR}/database"
    mkdir -p ${RALLY_DATABASE_DIR} ${RALLY_CONFIGURATION_DIR} /opt/rally/plugins /var/log/rally
    cp -r ${TOP_DIR}/rally_plugins/* /opt/rally/plugins
    cp -r ${TOP_DIR}/rally_apps/*  /opt/stack/rally

    RALLY_DATABASE_URL=${RALLY_DATABASE:-sqlite:///${RALLY_DATABASE_DIR}/rally.sqlite}

    sed -r \
     -e 's|^#(connection).*$|\1='${RALLY_DATABASE_URL}'|' \
     -e 's|^#(log_file).*$|\1=/var/log/job-reports/rally.log|'  \
     -e 's|^#(debug).*$|\1=True|' \
     -e 's|^#(cluster_create_timeout).*$|\1=3600|' \
     -e 's|^#(cluster_delete_timeout).*$|\1=3600|' \
     -e 's|^#(job_execution_timeout).*$|\1=3600|' \
     ${RALLY_DIR}/etc/rally/rally.conf.sample > ${RALLY_CONFIGURATION_DIR}/rally.conf

    if [ "${RALLY_DATABASE_URL%%:*}" == "sqlite" ]
    then
        ${VIRTUALENV_DIR}/bin/rally-manage db recreate
    fi

    chmod -R o+w ${RALLY_DATABASE_DIR} ${RALLY_CONFIGURATION_DIR} /opt/rally/plugins /var/log/rally

    RALLY_CLUSTER_FILE="`mktemp`"
    cat > ${RALLY_CLUSTER_FILE} << EOF
{
    "type": "ExistingCloud",
    "auth_url": "${OS_AUTH_URL}",
    "region_name": "RegionOne",
    "endpoint_type": "public",
    "admin_port": 35357,
    "admin": {
        "username": "${OS_ADMIN_USERNAME}",
        "password": "${OS_ADMIN_PASSWORD}",
        "tenant_name": "${OS_ADMIN_TENANT_NAME}"
    }
}
EOF

    ${VIRTUALENV_DIR}/bin/rally deployment create --filename=${RALLY_CLUSTER_FILE} --name=${SCALE_LAB_UUID} || :
    ${VIRTUALENV_DIR}/bin/rally deployment use --deployment ${SCALE_LAB_UUID}
    ${VIRTUALENV_DIR}/bin/rally deployment check

    # copy Rally scenarios into /opt/stack
    cp -r ${TOP_DIR}/../../../../mos-scenarios/rally-scenarios ${DEST}/
    cp -r ${TOP_DIR}/../../../../mos-scenarios/other-rally-scenarios ${DEST}/

    # copy Rally deployment openrc
    cp -r /root/.rally ${USER_HOME}
    #Fix permissions
    chown -R ${USER_NAME} ${VIRTUALENV_DIR}
    chown -R ${USER_NAME} ${USER_HOME}
    chown -R ${USER_NAME} ${DEST}
    chown -R ${USER_NAME} /var/log/job-reports
}

prepare_cloud_for_rally() {
    echo "Creating tenant 'demo'"
    keystone tenant-create --name demo || true
    echo "Creating user 'demo'"
    keystone user-create --tenant demo --name demo --pass demo || true
    echo "Assign role 'admin' to user 'admin' in tenant 'demo'"
    keystone user-role-add --user admin --role admin --tenant demo || true
    echo "Add role ResellerAdmin"
    keystone role-create --name ResellerAdmin || true
    echo "Add role anotherrole"
    keystone role-create --name anotherrole || true
    echo "Assign role 'anotherrole' to user 'demo' in tenant 'demo'"
    keystone user-role-add --user demo --role anotherrole --tenant demo || true
    echo "Adding flavor 'm1.nano'"
    nova flavor-create m1.nano 41 64 0 1 || true
    echo "Adding flavor 'm1.tempest-micro'"
    nova flavor-create m1.tempest-micro 42 128 0 1 || true

    echo "Add roles for Heat"
    keystone role-create --name heat_stack_user || true
    keystone role-create --name heat_stack_owner || true
    keystone user-role-add --user demo --role heat_stack_owner --tenant demo || true
    keystone user-role-add --user admin --role heat_stack_owner --tenant demo || true
    keystone user-role-add --user admin --role heat_stack_owner --tenant admin || true

    echo "Create role 'SwiftOperator' for Swift"
    keystone role-create --name SwiftOperator || true

    echo "Create image for Sahara"
    local uploaded="$(mktemp)"
    wget -q -O "$uploaded" "$SAHARA_IMAGE_URL"
    glance image-create \
        --name "$SAHARA_IMAGE_NAME" \
        --disk-format qcow2 \
        --container-format bare \
        --file "$uploaded" > /dev/null || true
    rm "$uploaded"
}

main() {
    . ${VIRTUALENV_DIR}/bin/activate
    . ${USER_HOME}/openrc
    cd ${TOP_DIR}
    install_helpers
    install_rally
    prepare_cloud_for_rally
    configure_rally
    cd -
}

main "$@"

