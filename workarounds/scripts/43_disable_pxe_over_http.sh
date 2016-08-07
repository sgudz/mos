#!/bin/bash
PATTERN="dhcp-option-force=210,http"
CONFIG="/etc/dnsmasq.d/default.conf"

dockerctl shell cobbler grep -q "^\w*${PATTERN}" ${CONFIG}
if [ $? == 0 ]; then
  dockerctl shell cobbler sed "/${PATTERN}/s/^/# /g" -i ${CONFIG}
  dockerctl shell cobbler systemctl restart dnsmasq
fi
