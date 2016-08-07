#!/bin/bash

# Collecting rabbitmq statistics
# Related bugs: https://bugs.launchpad.net/fuel/+bug/1460762
#               https://bugs.launchpad.net/fuel/+bug/1463433

#wget http://172.16.44.5/for_workarounds/37_rabbit_stat/rabbit_stat.sh -O /etc/puppet/modules/anacron/files/rabbit_stat.sh
#wget http://172.16.44.5/for_workarounds/37_rabbit_stat/rabbit_stat.cron -O /etc/puppet/modules/anacron/files/rabbit_stat
#curl -s 'http://172.16.44.5/for_workarounds/37_rabbit_stat/rabbit_stat.patch' | patch -b -d /etc/puppet/modules -p1

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_CMD="ssh ${SSH_OPTS}"

for controller in ${CONTROLLERS[*]}
do
  ${SSH_CMD} ${controller} "wget http://172.16.44.5/for_workarounds/37_rabbit_stat/rabbit_stat.sh -O /usr/bin/rabbit_stat.sh"
  ${SSH_CMD} ${controller} "chmod 0755 /usr/bin/rabbit_stat.sh"
  ${SSH_CMD} ${controller} "wget http://172.16.44.5/for_workarounds/37_rabbit_stat/rabbit_stat.cron -O /etc/cron.d/rabbit_stat"
done
