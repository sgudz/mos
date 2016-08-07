#!/bin/bash

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

# Common SSH options
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_CMD="ssh ${SSH_OPTS}"

${SSH_CMD} ${CONTROLLERS[0]} ". ./openrc; nova flavor-list | grep nano >/dev/null && echo "nano flavor is already exists" || nova flavor-create m1.nano 41 64 0 1"
