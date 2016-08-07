#!/bin/bash -x

# IP-address or resolvable name of Fuel-master
if [ -z "${FUEL_IP}" ]
then
  echo "\$FUEL_IP must be set"
  exit 1
fi

# Unprivileged user to run tests
USER_NAME=developer

# Shaker install path
SHAKER_PATH=/opt/stack/shaker

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

# SCP used only to obtain private SSH key of unprivileged user
SCP_CMD="sshpass -p r00tme scp ${SSH_OPTS} root@${FUEL_IP}"

# All work will be done by unprivileged user named ${USER_NAME}
SSH_CMD="ssh ${SSH_OPTS} -i id_rsa.${USER_NAME} ${USER_NAME}@${FUEL_IP}"

# Will be used for test_results publishing
TIME="MSK-$(date +%Y-%m-%d-%H:%M:%S)"

echo -n "Begin Shaker test(s) at "
date

# Get SSH private key of unprivileged user for futher use
# SSH keys are generated in time of fuel-master installation for user root,
# then copied to unprivileged user at tests preparation.
${SCP_CMD}:/home/developer/.ssh/id_rsa id_rsa.${USER_NAME}

# Prepare temporary directory for report(s)
# If use same directory, it may contain some reports for test(s) that will not
# be run on this execution
REPORTS_DIR=`${SSH_CMD} "mktemp -d"`

# Create script on remote node to run test
REMOTE_SCRIPT=`${SSH_CMD} "mktemp"`
${SSH_CMD} "cat > ${REMOTE_SCRIPT}" <<EOF
#!/bin/bash -xe

SHAKER_PATH=${SHAKER_PATH}
TEST_SUBJECT=${TEST_SUBJECT:-networking}

# Prepare environment
test -f /home/developer/openrc        && source /home/developer/openrc
test -f /opt/stack/.venv/bin/activate && source /opt/stack/.venv/bin/activate

# Disable neutron quotas
for res in floatingip  network port router security_group  security_group_rule subnet ; do
  neutron quota-update --\${res} -1
done

# Disable nova quotas
OS_TENANT_ID=\$(keystone tenant-get \${OS_TENANT_NAME} | awk '\$2 == "id" {print \$4}')
for res in ram cores instances; do
  nova quota-update --\${res} -1 \${OS_TENANT_ID}
done

cd \${SHAKER_PATH}

# Prepare Shaker OS image if it doesn't exists
if ! glance image-show shaker-image
then
  if [ -x /opt/stack/.venv/bin/shaker-image-builder ]
  then
    /opt/stack/.venv/bin/shaker-image-builder
  else
    \${SHAKER_PATH}/bin/prepare.sh
  fi
fi

# Run Shaker
for scenario_file in /opt/stack/shaker-scenarios/\${TEST_SUBJECT}/${TEST_GLOB:-*.yaml}
do
  scenario_name=\${scenario_file##*/}
  scenario_name=\${scenario_name%.*}
  echo -n "Run Shaker scenario \${scenario_name} at "
  date
  time shaker --debug \
    --scenario \${scenario_file} \
    --report ${REPORTS_DIR}/\${scenario_name}.html \
    --output ${REPORTS_DIR}/\${scenario_name}.json \
    --subunit ${REPORTS_DIR}/\${scenario_name}.subunit \
    --log-file ${REPORTS_DIR}/\${scenario_name}.log
done
cd -
EOF

# Run script on remote node and get exit code
${SSH_CMD} "bash -xe ${REMOTE_SCRIPT}"

# Delete script on remote node
${SSH_CMD} "rm -f ${REMOTE_SCRIPT}"

# Generate node list
NODELIST=${REPORTS_DIR}/_nodelist.html
${SSH_CMD} "cat > ${NODELIST}" <<EOF
<html>
<head>
 <title>Cluster node list</title>
 <style type="text/css">
  table {border-collapse: collapse; width: 100%; font-family: monospace;}
  table, th {border: 2px solid black;}
  td {border: 1px solid black;}
 </style>
</head>
<body>
 <table>
  <tr><th>Hostname</th><th>Name</th><th>IP address</th><th>MAC address</th><th>Roles</th></tr>
EOF

${SSH_CMD} "fuel nodes | awk -F\\| 'function trim(string) {return gensub(/(^ +)|( +)\$/, \"\", \"g\", string)} trim(\$2) == \"ready\" {printf(\"  <tr><td>node-%d</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>\\n\", trim(\$1), trim(\$3), trim(\$5), trim(\$6), trim(\$7))}' >> ${NODELIST}"

${SSH_CMD} "cat >> ${NODELIST}" <<EOF
 </table>
</body>
</html>
EOF

# Jenkins not clears workdir between runs
rm -f *.html *.log
# Copy reports and remove temporary directory
${SCP_CMD}:${REPORTS_DIR}/* .
${SSH_CMD} "rm -rf ${REPORTS_DIR}"

echo -n "End Shaker test(s) at "
date

# Prepare some data for test_results page
RESULTS_ROOT_DIR="/var/www/test_results"
FUEL_BUILD_NUMBER=`${SSH_CMD} "fuel --fuel-version 2>&1 | awk '/^release:/ {VERSION=gensub(/[^0-9\.]/, \"\", \"g\", \\$2)} /^build_number:/ {BUILD=gensub(/[^0-9\.]/, \"\", \"g\", \\$2)} END {printf(\"%s-%s\n\", VERSION, BUILD)}'"`
RESULTS_DIR=${RESULTS_ROOT_DIR}/build_${FUEL_BUILD_NUMBER}
TIME="${TIME}-$(date +%Y-%m-%d-%H:%M:%S)"
DIR_NAME=${BUILD_TAG}-${TIME}

test -d ${RESULTS_DIR}/${DIR_NAME}/ || mkdir -p ${RESULTS_DIR}/${DIR_NAME}/
cp *.json *.html *.log ${RESULTS_DIR}/${DIR_NAME}/
${SCP_CMD}:/root/cluster.cfg ${RESULTS_DIR}/${DIR_NAME}/ || :
echo "{\"type\": \"${EXECUTION_TYPE}\"}" > ${RESULTS_DIR}/${DIR_NAME}/executor_settings.json
