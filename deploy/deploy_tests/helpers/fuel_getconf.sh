#!/bin/bash

FUEL_USER=admin
FUEL_PASS=admin

FUEL_ADDR=localhost

AUTH_TOKEN=""

function keystone_auth() {
AUTH_TOKEN=`fuel token`
}

function keystone_deauth() {
curl \
 --silent \
 --request DELETE \
 --header "X-Auth-Token: ${AUTH_TOKEN}" \
 --header "X-Subject-Token: ${AUTH_TOKEN}" \
 http://${FUEL_ADDR}:5000/v3/auth/tokens
}

function nailgun_query() {
curl \
 --silent \
 --header "X-Auth-Token: ${AUTH_TOKEN}" \
 http://${FUEL_ADDR}:8000/api/${1:-releases}
}

keystone_auth

if [ -z "${CLUSTER_ID}" ]
then
  CLUSTER_ID=`nailgun_query clusters | awk 'BEGIN{ RS=","; FS=":"; } gensub(/\\W/, "", "g", $1) == "id" { gsub(/\\W/, "", $2); print $2; exit }'`
fi

FUEL_CONF=`nailgun_query clusters/${CLUSTER_ID} | sed "s/'/''/g"`
CLUSTER_CONF=`nailgun_query clusters/${CLUSTER_ID}/attributes | sed "s/'/''/g"`
NETWORK_CONF=`nailgun_query clusters/${CLUSTER_ID}/network_configuration/neutron | sed "s/'/''/g"`
NODES_CONF=`nailgun_query nodes | sed "s/'/''/g"`
RELEASES_CONF=`nailgun_query releases | sed "s/'/''/g"`
NODEALLOCATION_CONF=`nailgun_query nodes/allocation/stats | sed "s/'/''/g"`

keystone_deauth

if [ "${RALLY_DATABASE%%:*}" == "postgresql" ]
then
  sql_cmd=`mktemp`
cat > ${sql_cmd} <<EOF
DELETE FROM cluster_config WHERE uuid='${SCALE_LAB_UUID}';
INSERT INTO cluster_config
  (uuid, env, attributes, network, nodes, fuel, releases, rally_version, node_allocation)
 VALUES (
  '${SCALE_LAB_UUID}',
  '${SCALE_LAB_ENV}',
  '${CLUSTER_CONF}',
  '${NETWORK_CONF}',
  '${NODES_CONF}',
  '${FUEL_CONF}',
  '${RELEASES_CONF}',
  '${RALLY_VERSION}',
  '${NODEALLOCATION_CONF}'
 );
EOF
  psql ${RALLY_DATABASE} -f ${sql_cmd}
  rm -f ${sql_cmd}
fi
