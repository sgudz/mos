#!/bin/bash
# To avoid clearing rabbitmq logs
# Related bug: https://bugs.launchpad.net/fuel/+bug/1473405

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_CMD="ssh ${SSH_OPTS}"

for controller in ${CONTROLLERS[*]}
do
  ${SSH_CMD} ${controller} "sed -i s/\"\/etc\/init.d\/rabbitmq-server rotate-logs > \/dev\/null\"/\"DATE=-\\\`date +%y_%m_%d_%H_%M_%S\\\`; rabbitmqctl rotate_logs \\\${DATE}\"/ /etc/logrotate.d/rabbitmq-server"
done
