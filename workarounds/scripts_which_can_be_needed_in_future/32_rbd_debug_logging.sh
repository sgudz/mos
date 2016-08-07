#!/bin/bash
# Add dbug logging for ceph-rbd. Needed for trbleshooting the bug https://bugs.launchpad.net/mos/+bug/1459781

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_CMD="ssh ${SSH_OPTS}"

for controller in ${CONTROLLERS[*]}
do
  ${SSH_CMD} ${controller} "grep librbd /etc/ceph/ceph.conf"
  if [ $? == 1 ]
  then
      ${SSH_CMD} ${controller} "sed -i s/\"\[client\]\"/\"\[client\]\ndebug rbd = 20\ndebug librbd = 20\nlog file = \/var\/log\/ceph\/ceph.client.log\ndebug ms = 1\"/ /etc/ceph/ceph.conf"
      if [ `grep operating_system /root/cluster.cfg | awk -F"=" {'print $2'} | sed s/" "//g` == 'ubuntu' ]
      then
         ${SSH_CMD} ${controller} "service cinder-volume restart"
      else
         ${SSH_CMD} ${controller} "/etc/init.d/openstack-cinder-volume restart"
      fi
  fi
done
