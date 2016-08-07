#!/bin/bash -xe

WS=${WORKSPACE}
FI=${FUEL_IP}
GERRIT_USER=${GERRIT_USER:-mos-scale-jenkins}
GERRIT_KEY=${GERRIT_KEY:-mos-scale-jenkins}
GIT_SCENARIOS_BRANCH=${SCENARIOS_VERSION:-origin/master}

GIT_SCENARIOS="ssh://${GERRIT_USER}@gerrit.mirantis.com:29418/mos-scale/mos-scenarios"


if [ -n "$WS" ]; then
    cd ${WS}
else
   echo "\$WORKSPACE must be set"
   exit 1
fi
if [ -z "$FI" ]; then
   echo "\$FUEL_IP must be set"
   exit 1
fi
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
SSH_CMD="sshpass -p r00tme ssh ${SSH_OPTS} root@${FI}"
SCP_CMD="sshpass -p r00tme scp ${SSH_OPTS}"
${SSH_CMD} "echo export REFSPEC=${REFSPEC}               >  /etc/profile.d/jenkins_job.env.sh"
${SSH_CMD} "echo export BRANCH=${BRANCH}                 >> /etc/profile.d/jenkins_job.env.sh"
${SSH_CMD} "echo export RALLY_DATABASE=${RALLY_DATABASE} >> /etc/profile.d/jenkins_job.env.sh"
${SSH_CMD} "echo export RALLY_VERSION=${RALLY_VERSION:-0.0.3} >> /etc/profile.d/jenkins_job.env.sh"
${SSH_CMD} "echo export USE_PROXY=${USE_PROXY} >> /etc/profile.d/jenkins_job.env.sh"
${SSH_CMD} "echo export EXECUTION_TYPE=${EXECUTION_TYPE} > /etc/profile.d/jenkins_exe.env.sh"
${SSH_CMD} "echo export ABORT_ON_SLA_FAILURE=${ABORT_ON_SLA_FAILURE} >> /etc/profile.d/jenkins_exe.env.sh"
${SSH_CMD} "echo export FUEL_IP=${FI} >> /etc/profile.d/jenkins_exe.env.sh"
DEPL_DIR="/tmp/rally_tempest_deploy"
TMP_DIR=$(mktemp -d)

#Get scenarios
eval `ssh-agent -s`
ssh-add ~/.ssh/${GERRIT_KEY}
rm -rf ./mos-scenarios
git clone ${GIT_SCENARIOS}
cd ./mos-scenarios
git checkout ${GIT_SCENARIOS_BRANCH}
cd -
rm -r mos-scenarios/.git
kill ${SSH_AGENT_PID}

tar -czvf ${TMP_DIR}/rally_tempest_deploy_script.tar.gz *
${SSH_CMD} rm -rf /tmp/rally_tempest_deploy_script.tar.gz
${SSH_CMD} rm -rf /opt/stack/.venv
${SCP_CMD} ${TMP_DIR}/rally_tempest_deploy_script.tar.gz root@${FI}:/tmp/
rm -rf ${TMP_DIR}
${SSH_CMD} rm -rf ${DEPL_DIR}
${SSH_CMD} mkdir ${DEPL_DIR}
${SSH_CMD} tar -xzvf /tmp/rally_tempest_deploy_script.tar.gz -C ${DEPL_DIR}
${SSH_CMD} bash -c "${DEPL_DIR}/deploy/deploy_tests/install_tests.sh"

echo "Add SaharaVanilla image UUID to environment"
SAHARA_IMAGE_UUID=`${SSH_CMD} '. /home/developer/openrc && . /opt/stack/.venv/bin/activate && glance image-list | grep SaharaVanilla | head -n 1 | cut -d" " -f2'`
${SSH_CMD} "echo export SAHARA_IMAGE_UUID=${SAHARA_IMAGE_UUID} >> /etc/profile.d/jenkins_job.env.sh"
