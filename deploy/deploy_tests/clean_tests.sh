#!/bin/bash -xe

rm -rf /opt/stack
userdel developer
rm -rf /home/developer/

# Remove all directories created by install.sh
rm -rf \
 /etc/tempest \
 /etc/rally \
 /etc/shaker \
 /opt/rally/plugins \
 /var/log/rally \
 /var/lib/elk \
 /var/log/elk \
 /var/log/job-reports
