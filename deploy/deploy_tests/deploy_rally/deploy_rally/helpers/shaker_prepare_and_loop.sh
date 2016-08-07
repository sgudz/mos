#!/bin/bash -xe

SHAKER_PATH=/opt/stack/shaker
MAIN_SCENARIO=$1
BIN_DIR=/opt/stack/.venv/bin

# Prepare environment
test -f /home/developer/openrc        && source /home/developer/openrc
test -f /opt/stack/.venv/bin/activate && source /opt/stack/.venv/bin/activate

# Disable neutron quota
for res in floatingip  network port router security_group  security_group_rule subnet ; do
  neutron quota-update --${res} -1
done
# Disable nova quota
OS_TENANT_ID=$(keystone tenant-get ${OS_TENANT_NAME} | awk '$2 == "id" {print $4}')
for res in instances cores ram server_groups server_group_members ; do
    nova quota-update --${res} -1 ${OS_TENANT_ID}
done

cd ${SHAKER_PATH}

# Prepare Shaker OS image if it doesn't exists
if ! glance image-show shaker-image
then
  /opt/stack/.venv/bin/shaker-image-builder
fi
# Commented to SIGINT shaker support
# Prepare tests for run within 15 hours
# sed -i 's/time: 60/time: 54000/g' ${MAIN_SCENARIO}
sed -i 's/time: 60$/time: 600/g' ${MAIN_SCENARIO}
sed -i '/size:/d' ${MAIN_SCENARIO}
# Run Shaker
# While  shaker not  support SIGINT

while [ -z '' ]; do
    ${BIN_DIR}/python ${BIN_DIR}/shaker --debug --no-report-on-error --scenario ${MAIN_SCENARIO} --report /var/log/job-reports/shaker_report-$(date +%F-%T).html
done
