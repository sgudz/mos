#!/bin/bash -xe

#
# This script fetches known cluster parameters from remote host (fuel-master),
# stores it in file within directory with workaround , and runs all found
# in that directory scripts in turn.
#
# Workaround scripts may use any avalable tools and/or languages, but to use
# environment variables you must source/evaluate file ".cluster_info"
# in your script.
#

# IP-address or resolvable name of Fuel-master
if [ -z "${FUEL_IP}" ]
then
  echo "\$FUEL_IP must be set"
  exit 1
fi

if [ "${LAB_NAME}" == "rackspace-1" ]
then
  WORKAROUNDS_DIR=scripts_rackspace-1
else
  WORKAROUNDS_DIR=scripts
fi

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'

# SCP used mostly to obtain private SSH key(s)
SCP_CMD="sshpass -p r00tme scp ${SSH_OPTS}"

# All work may be done by unprivileged user named ${USER_NAME}
SSH_CMD="ssh ${SSH_OPTS} -i id_rsa.${USER_NAME:-root} ${USER_NAME:-root}@${FUEL_IP}"

# Get SSH private key of unprivileged user for futher use
# SSH keys are generated in time of fuel-master installation for user root,
# then copied to unprivileged user at tests preparation.
${SCP_CMD} ${USER_NAME:-root}@${FUEL_IP}:~/.ssh/id_rsa id_rsa.${USER_NAME:-root}

# Prepare temporary directory for scripts
SCRIPTS_DIR=`${SSH_CMD} "mktemp -d"`

if [ -z "${WORKSPACE}"  ]; then
   echo "\$WORKSPACE must be set"
   exit 1
fi

source ${WORKSPACE}/helpers/fuel_version.sh

# Get operating systems for releases
eval `${SSH_CMD} "fuel release" \
 | awk -F\| '/^[0-9]/ {printf("RELEASES[%d]=%s\n", $1, gensub(" ","","g",$4))}'`

# If clusters not available, skip info gathering about it
if [ ${CLUSTER_COUNT} -gt 0 ]
then
  CLUSTER_NUMBERS=( ${!CLUSTERS[*]} )

  CLUSTER=${CLUSTER:-${CLUSTER_NUMBERS[0]}}
  echo "Using environment #${CLUSTER}"

  OS=${RELEASES[${CLUSTERS[${CLUSTER}]}]}

  # Get clusters info
  ${SSH_CMD} "fuel network  --env ${CLUSTER} --download --dir ${SCRIPTS_DIR}"
  ${SSH_CMD} "fuel settings --env ${CLUSTER} --download --dir ${SCRIPTS_DIR}"
  eval `${SSH_CMD} "fuel --env ${CLUSTER} node" \
   | awk -F\| '
     $7 ~ /compute/    {COMPUTES=COMPUTES $5}
     $7 ~ /controller/ {CONTROLLERS=CONTROLLERS $5}
     END {printf("COMPUTES=(%s)\nCONTROLLERS=(%s)\n", COMPUTES, CONTROLLERS)}'`

  ${SCP_CMD} ${USER_NAME:-root}@${FUEL_IP}:${SCRIPTS_DIR}/*.yaml . || :
  ${SSH_CMD} "rm -f ${SCRIPTS_DIR}/*.yaml"

  SEGMENTATION_TYPE=`grep segmentation_type network_${CLUSTER}.yaml | tr -d " " | cut -f2 -d:`
fi

# Display info about environment
cat <<EOF
Environment #${CLUSTER} (total available ${CLUSTER_COUNT})

  Fuel version: ${FUEL_VERSION}-${FUEL_BUILD}

  Operating system on nodes: ${OS}

  Number of nodes
     Controllers:  ${#CONTROLLERS[*]}
     Computes:     ${#COMPUTES[*]}

  Network segmentation: ${SEGMENTATION_TYPE}
EOF

MAIN_OS=`echo ${OS} | tr [:upper:] [:lower:]`

# Prepare cluster parameters file that may be sourced by workaround scripts
${SSH_CMD} "cat > ${SCRIPTS_DIR}/.cluster_info" <<EOF
FUEL_IP=${FUEL_IP}
ENV_NUMBER=${FUEL_IP##*.}

FUEL_VERSION=${FUEL_VERSION}
FUEL_RELEASE=${FUEL_VERSION}
FUEL_BUILD=${FUEL_BUILD}
FUEL_BUILD_NUMBER=${FUEL_VERSION}-${FUEL_BUILD}

CLUSTER_COUNT=${CLUSTER_COUNT}
CLUSTER_NUMBERS=( ${CLUSTER_NUMBERS[*]} )
CLUSTER=${CLUSTER}

CONTROLLER_COUNT=${#CONTROLLERS[*]}
COMPUTE_COUNT=${#COMPUTES[*]}
NODE_COUNT=$(( ${#CONTROLLERS[*]} + ${#COMPUTES[*]} ))

SEGMENTATION_TYPE=${SEGMENTATION_TYPE}

MAIN_OS=${MAIN_OS}
OS=${OS}

CONTROLLERS=( ${CONTROLLERS[*]} )
COMPUTES=( ${COMPUTES[*]} )
EOF

echo "Enviroment variables available to other scripts"
${SSH_CMD} "cat ${SCRIPTS_DIR}/.cluster_info"

# Copy scripts to remote host
${SCP_CMD} ${0%/*}/${WORKAROUNDS_DIR}/* ${USER_NAME:-root}@${FUEL_IP}:${SCRIPTS_DIR}/
${SSH_CMD} "chmod a+x ${SCRIPTS_DIR}/*"

# Run scripts
${SSH_CMD} "for script in ${SCRIPTS_DIR}/*; do \${script}; done"

# Remove scripts
${SSH_CMD} "rm -rf ${SCRIPTS_DIR}"
