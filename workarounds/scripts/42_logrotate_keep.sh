#!/bin/bash
# Change number of log archives to 1000
curl -s 'http://172.16.44.5/for_workarounds/42_logrotate_keep/logrotate_keep.patch' | patch -b -d /etc/puppet/modules -p1
