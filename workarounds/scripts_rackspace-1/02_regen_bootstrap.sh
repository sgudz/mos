#!/bin/bash
# https://bugs.launchpad.net/fuel/+bug/1543233

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

mkdir /usr/share/fuel_bootstrap_cli/files/trusty/etc/fuel-agent || :
curl -s 'http://paste.openstack.org/raw/506300/' > /usr/share/fuel_bootstrap_cli/files/trusty/etc/fuel-agent/fuel-agent.conf
NEW_IMAGE=`fuel-bootstrap build | grep "has been built: " | awk '{print $NF}'`
fuel-bootstrap import ${NEW_IMAGE} --activate
