#!/bin/bash

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

# SKIP FOR FULL RALLY
if [ -w /opt/stack/.venv/etc/skip_test.txt ];
then
	cat << EOF >> /opt/stack/.venv/etc/skip_test.txt
# to avoid skipping all scenarios
nothing
# doesn't work with new rally
murano/create_and_deploy_environment.yaml
EOF
# SKIP FOR FULL RALLY FOR VLAN-SEGMENTATION CASE
	if [ "${SEGMENTATION_TYPE}"  == "vlan" ];
	then
		 cat << EOF >> /opt/stack/.venv/etc/skip_test.txt
# need 2000 VLANs
mox/boot_server_with_network_in_single_tenant.yaml
EOF
	fi
else
	echo "skip_test.txt doesn't exist. Have you prepared the master node?";
fi

# SKIP FOR RALLY LIGHT
if [ -w /opt/stack/.venv/etc/skip_test_light.txt ];
then
        cat << EOF >> /opt/stack/.venv/etc/skip_test_light.txt
# to avoid skipping all scenarios
nothing
# doesn't work with new rally
murano/create_and_deploy_environment.yaml
EOF
else
        echo "skip_test_light.txt doesn't exist. Have you prepared the master node?";
fi
