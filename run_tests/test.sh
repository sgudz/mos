#!/bin/bash
#set -x
#This script should be run from the Master node in order to install and launch Shaker
#This script tests "storage" network for test between nodes. You can change network by replacing NETWORK parameter(to do).
export DATE=`date +%Y-%m-%d_%H:%M`

export SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
CONTROLLER_ADMIN_IP=`fuel node | grep controller | awk -F "|" '{print $5}' | sed 's/ //g' | head -n 1`

export CONTROLLER_PUBLIC_IP=$(ssh ${CONTROLLER_ADMIN_IP} "ifconfig | grep br-ex -A 1 | grep inet | awk ' {print \$2}' | sed 's/addr://g'")
echo "Controller Public IP: $CONTROLLER_PUBLIC_IP"

##################################### Run Shaker on Controller ##########################
echo "Install Shaker on Controller"
REMOTE_SCRIPT=`ssh $CONTROLLER_ADMIN_IP "mktemp"`
ssh ${SSH_OPTS} $CONTROLLER_ADMIN_IP "cat > ${REMOTE_SCRIPT}" <<EOF
#set -x
source /root/openrc
SERVER_ENDPOINT=$CONTROLLER_PUBLIC_IP
printf 'deb http://ua.archive.ubuntu.com/ubuntu/ trusty universe' > /etc/apt/sources.list
apt-get update
apt-get -y --force-yes install iperf python-dev libzmq-dev python-pip && pip install pbr pyshaker
iptables -I INPUT -s 10.0.0.0/16 -j ACCEPT
iptables -I INPUT -s 172.16.0.0/16 -j ACCEPT
iptables -I INPUT -s 192.168.0.0/16 -j ACCEPT
shaker-image-builder --flavor-vcpu 8 --flavor-ram 4096 --flavor-disk 55 --debug
SERVER_ENDPOINT=$CONTROLLER_PUBLIC_IP
SERVER_PORT=18000
shaker --server-endpoint \$SERVER_ENDPOINT:\$SERVER_PORT --scenario /usr/local/lib/python2.7/dist-packages/shaker/scenarios/openstack/VMs.yaml --report VMs_$DATE.html --debug
EOF
#Run script on remote node
ssh ${SSH_OPTS} $CONTROLLER_ADMIN_IP "bash ${REMOTE_SCRIPT}"
