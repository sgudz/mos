#!/bin/bash -x

SCRIPT_FILE=$(basename $0)

FUEL_IP=${FUEL_IP:-172.16.44.10}
SMOKE=${SMOKE:-0}
export SMOKE
LOAD_FACTOR=${LOAD_FACTOR:-1}
export LOAD_FACTOR
RESULTS_ROOT_DIR="/var/www/test_results"
TIME="MSK-$(date +%Y-%m-%d-%H:%M:%S)"
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_CMD="sshpass -p r00tme ssh -t -t ${SSH_OPTS} root@${FUEL_IP}"
SCP_CMD="sshpass -p r00tme scp ${SSH_OPTS} "

USAGE="$SCRIPT_FILE  -t \"testcases\" (optional) [-h] -- script for run tests

where:
    -t testcases

WARINIG ! if '-r all' then -t WILL BE IGNORED"

while getopts :r:t: option; do
  case "$option" in
    t) TESTS_CASES="$OPTARG";;
    *) echo "$USAGE"
       exit
       ;;
   esac
done
shift $(($OPTIND-1))

if [ -z "${WORKSPACE}"  ]; then
   echo "\$WORKSPACE must be set"
   exit 1
fi

source ${WORKSPACE}/helpers/fuel_version.sh

# Get operating systems for releases
eval `${SSH_CMD} "fuel release" \
 | awk -F\| '/^[0-9]/ {printf("RELEASES[%d]=%s\n", $1, gensub(" ", "", "g", $4))}'`

# Use first ID from array as cluster ID if it unset
CLUSTER=${CLUSTER:-${CLUSTER_NUMBERS[0]}}
echo "Using environment #${CLUSTER}"

MAIN_OS=`echo ${RELEASES[${CLUSTERS[${CLUSTER}]}]} | tr [:upper:] [:lower:]`

RESULTS_DIR=${RESULTS_ROOT_DIR}/build_${FUEL_BUILD_NUMBER}

if [ -z "${FUEL_BUILD_NUMBER}"  ]; then
    echo "Can't find build number"
    exit 1
fi

if [ -z "${MAIN_OS}"  ]; then
    echo "Can't find OS"
    exit 1
fi

SCRIPT=$(mktemp)
cat << EOF > ${SCRIPT}
#!/bin/bash -xe
. /opt/stack/.venv/bin/activate
. /home/developer/openrc

if [ "\${RALLY_DATABASE%%:*}" == "postgresql" ]
then
  # Delete tasks in running state on THIS environment
  psql \${RALLY_DATABASE} -c "DELETE FROM tasks t USING deployments d WHERE t.status='running' and d.name='\${SCALE_LAB_UUID}' and t.deployment_uuid = d.uuid" || :

  # Delete tasks running on cluster(s) that no longer exists
  psql \${RALLY_DATABASE} -c "SELECT * FROM clean_running_tasks()" || :
fi
EOF

if [ -z "${TESTS_CASES}" ]; then
   TESTS_CASES='all'
fi
echo "/opt/stack/.venv/bin/run_rally --task ${TESTS_CASES}" >> ${SCRIPT}

echo "Delete old remote reports and local xml"
rm -rf ${WORKSPACE}/*.xml
${SSH_CMD} rm -rf /var/log/job-reports/'*'
echo "Check deleting"
${SSH_CMD} ls -la /var/log/job-reports/
ls -l ${WORKSPACE}/*.xml

# Push Jenkins' environment variables to host running tests
${SSH_CMD} "echo export BUILD_NUMBER=${BUILD_NUMBER}  >  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export BUILD_TAG=${BUILD_TAG}       >>  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export BUILD_URL=${BUILD_URL}       >>  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export JENKINS_URL=${JENKINS_URL}   >>  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export JOB_NAME=${JOB_NAME}         >>  /etc/profile.d/jenkins_build.env.sh"

${SSH_CMD} "echo export EXECUTION_TYPE=${EXECUTION_TYPE} > /etc/profile.d/jenkins_exe.env.sh"
${SSH_CMD} "echo export ABORT_ON_SLA_FAILURE=${ABORT_ON_SLA_FAILURE} >> /etc/profile.d/jenkins_exe.env.sh"

${SSH_CMD} "echo export SMOKE=${SMOKE} >>  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export LOAD_FACTOR=${LOAD_FACTOR} >>  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export SIM_RUNS=${SIM_RUNS} >>  /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export SHAKER_RUN=${SHAKER_RUN} >> /etc/profile.d/jenkins_build.env.sh"
${SSH_CMD} "echo export FUEL_VERSION=${FUEL_VERSION} >> /etc/profile.d/jenkins_build.env.sh"

# Append TestRail parameters and enable test results publishing
if [ "${EXECUTION_TYPE}" == "scale" ]
then
  if [ "${JOB_NAME##*_}" == "light" ]
  then
    TESTRAIL_TEST_SECTION=Light
  else
    TESTRAIL_TEST_SECTION=Full
  fi
  ${SSH_CMD} "echo export TESTRAIL_USER=${TESTRAIL_USER:-all@mirantis.com}      >>  /etc/profile.d/jenkins_build.env.sh"
  ${SSH_CMD} "echo export TESTRAIL_PASSWORD=${TESTRAIL_PASSWORD:-mirantis1C@@L} >>  /etc/profile.d/jenkins_build.env.sh"
  ${SSH_CMD} "echo export TESTRAIL_TEST_SUITE=${TESTRAIL_TEST_SUITE:-Rally}     >>  /etc/profile.d/jenkins_build.env.sh"
  ${SSH_CMD} "echo export TESTRAIL_TEST_SECTION=${TESTRAIL_TEST_SECTION}        >>  /etc/profile.d/jenkins_build.env.sh"
  echo "cd /tmp/rally_tempest_deploy/helpers/testrail/" >> ${SCRIPT}
  echo "/usr/bin/env python send_results.py || :"       >> ${SCRIPT}
fi

echo "Checking script before sending"
cat ${SCRIPT}

SCRIPT_FILE=$(basename ${SCRIPT})
${SCP_CMD} /tmp/${SCRIPT_FILE} root@${FUEL_IP}:/tmp/
${SSH_CMD} chmod 755 /tmp/${SCRIPT_FILE}
rm -rf ${SCRIPT}
${SSH_CMD} sudo -i -u developer /tmp/${SCRIPT_FILE}
${SSH_CMD} rm -rf /tmp/${SCRIPT_FILE}

echo "Get all config and reports file"
TIME="${TIME}-$(date +%Y-%m-%d-%H:%M:%S)"
if [ -z "${MAIN_OS}" ]; then
	DIR_NAME=${BUILD_TAG}-${TIME}
else
	DIR_NAME=${BUILD_TAG}-${MAIN_OS}-${TIME}
fi
mkdir -p ${RESULTS_DIR}/${DIR_NAME}
${SCP_CMD} -r root@${FUEL_IP}:/var/log/job-reports/'*' ${RESULTS_DIR}/${DIR_NAME}/
${SCP_CMD} -r root@${FUEL_IP}:/root/cluster.cfg ${RESULTS_DIR}/${DIR_NAME}/
${SCP_CMD} -r root@${FUEL_IP}:/opt/stack/executor_settings.json ${RESULTS_DIR}/${DIR_NAME}/
mkdir -p ${RESULTS_DIR}/${DIR_NAME}/logs
mv ${RESULTS_DIR}/${DIR_NAME}/*.log.gz ${RESULTS_DIR}/${DIR_NAME}/logs/
cp ${RESULTS_DIR}/${DIR_NAME}/*.xml ${WORKSPACE}/
cp ${RESULTS_DIR}/${DIR_NAME}/*.json  ${WORKSPACE}/

