#!/bin/bash
# To avoid rebbitmq restarting
# Related bug: https://bugs.launchpad.net/fuel/+bug/1479815
# Related fix: https://review.openstack.org/#/c/217738/

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_CMD="ssh ${SSH_OPTS}"

${SSH_CMD} ${CONTROLLERS[0]} "crm_resource --resource p_rabbitmq-server --set-parameter max_rabbitmqctl_timeouts --parameter-value 10" && sleep 600
