#!/bin/bash

[ -r ${0%/*}/.cluster_info ] && source ${0%/*}/.cluster_info

yum -y install patch
curl -s 'http://paste.openstack.org/raw/495857/' | patch -b -d / -p1
