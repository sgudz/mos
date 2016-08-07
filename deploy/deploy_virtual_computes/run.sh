#!/usr/bin/env bash
if [ -z "$1" ]; then
    NODES=10
else
    NODES=$1
fi
ansible-playbook -i hosts deploy.yaml -e nodes=${NODES}