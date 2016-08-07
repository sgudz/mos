#!/bin/bash

FUEL_VERSION=$(${SSH_CMD} fuel --version 2>&1 | tr -d '\r\n')
if [ "x${FUEL_VERSION}" == "x9.0.0" ]; then
    FUEL_BUILD=$(${SSH_CMD} cat /etc/fuel_build_number | tr -d '\r\n')
else
    FUEL_BUILD=$(${SSH_CMD} cat /etc/fuel/version.yaml | grep build_number | awk '{ print $2}' | tr -d '\r\n"')
fi
FUEL_BUILD_NUMBER="${FUEL_VERSION}-${FUEL_BUILD}"

# Get cluster info
eval `${SSH_CMD} "fuel2 env list -c id -c release_id -c status -f value" \
 | grep operational | awk '{printf("CLUSTERS[%d]=%d\n", $1, $3)}'`

CLUSTER_COUNT=${#CLUSTERS[*]}
CLUSTER_NUMBERS=( ${!CLUSTERS[*]} )
