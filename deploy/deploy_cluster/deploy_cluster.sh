#!/bin/bash -xe
WDIR=$(cd `dirname "${BASH_SOURCE[0]}"` && pwd)
cd ${WDIR}
SSH_OPTIONS="StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet"
SSH_PASSWORD="r00tme"
SSH_USER="root"

SSH_CMD="sshpass -p ${SSH_PASSWORD} ssh -o ${SSH_OPTIONS} ${SSH_USER}@${FUEL_IP}"
SCP_CMD="sshpass -p ${SSH_PASSWORD} scp -o ${SSH_OPTIONS} "
RSYNC_CMD="sshpass -p ${SSH_PASSWORD} rsync -v -e ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "

GIT_PRIVATE_BRANCH=${GIT_PRIVATE_BRANCH:-origin/master}
GIT_PRIVATE=${GIT_PRIVATE:-"ssh://mos-scale-jenkins@gerrit.mirantis.com:29418/mos-scale/mos-private"}
GIT_PRIVATE_KEY=${GIT_PRIVATE_KEY:-"mos-scale-jenkins"}

MAIN_OS=${MAIN_OS:-centos}
RELEASE_NAME=$(${SSH_CMD} "fuel release 2>/dev/null" | awk -F"|" -v OS=${MAIN_OS} 'tolower($4) ~ OS {split(gensub(/(^ | +$)+/, "", "g", $2), o, / /); print o[3], o[4]}' | head -n 1)
if [ $(wc -l <<< ${RELEASE_NAME}) -ne 1 ];
then
	echo "Os must be set"
	exit 1;
fi

LAB_NAME=${LAB_NAME:-mirantis-1}
FUEL_IP=${FUEL_IP:-172.16.44.10}
HYPERVISOR=${HYPERVISOR:-kvm}
MODE=${MODE:-ha_compact}
NETWORK_PROVIDER=${NETWORK_PROVIDER:-neutron}
PROVISION_METHOD=${PROVISION_METHOD:-cobbler}
SEGMENTATION_TYPE=${SEGMENTATION_TYPE:-gre}
LMA=${LMA:-false}
LMA_VERSION=${LMA_VERSION:-last_stable}
CONTROLLER_COUNT=${CONTROLLER_COUNT:-3}
COMPUTE_COUNT=${COMPUTE_COUNT:-95}
if [ "$LMA" = "true" ]; then
  NODE_COUNT=$((${COMPUTE_COUNT}+${CONTROLLER_COUNT}+2))
else
  NODE_COUNT=$((${COMPUTE_COUNT}+${CONTROLLER_COUNT}))
fi
CEPH_COUNT=${CEPH_COUNT:-$COMPUTE_COUNT}
VOLUMES_LVM=${VOLUMES_LVM:-false}
VOLUMES_CEPH=${VOLUMES_CEPH:-true}
IMAGES_CEPH=${IMAGES_CEPH:-true}
EPHEMERAL_CEPH=${EPHEMERAL_CEPH:-true}
OBJECTS_CEPH=${OBJECTS_CEPH:-true}
SAHARA=${SAHARA:-false}
CEILOMETER=${CEILOMETER:-false}
MURANO=${MURANO:-false}
CIDR=${CIDR:-172.16.44.0/22}
PUBLIC_RANGE=${PUBLIC_RANGE:-172.16.44.16-172.16.44.120}
GATEWAY=${GATEWAY:-172.16.44.1}
MANAGEMENT_VLAN=${MANAGEMENT_VLAN:-100}
STORAGE_VLAN=${STORAGE_VLAN:-101}
FLOATING_VLAN=${FLOATING_VLAN}
FLOATING_RANGE=${FLOATING_RANGE:-172.16.44.121-172.16.44.220}
FLOATING_VLAN_RANGE=${FLOATING_VLAN_RANGE}
NODE_MAX=${NODE_MAX:-100}
NODE_ADD=${NODE_ADD:-0}
POWER_ON_DELAY=${POWER_ON_DELAY:-5}
ENV_NUMBER=${ENV_NUMBER:-10}
DELETE_ENV=${DELETE_ENV:-false}
CONFIGURE_ONLY=${CONFIGURE_ONLY:-false}
CONFIGURE_SWITCHES=${CONFIGURE_SWITCHES:-false}
DEBUG=${DEBUG:-true}
NOVA_QUOTA=${NOVA_QUOTA:-false}
NETWORK_VERIFICATION=${NETWORK_VERIFICATION:-false}
CONTROLLER_MAC_LIST=${CONTROLLER_MAC_LIST}
DVR_ENABLE=${DVR_ENABLE:-true}
SSL_ENABLE=${SSL_ENABLE:-false}
TLS_ENABLE=${TLS_ENABLE:-false}
ETH0=${ETH0:-public}
ETH1=${ETH1}
ETH3=${ETH3}
UBUNTU_REPOSITORY=${UBUNTU_REPOSITORY:-"none"}
EXTRA_REPOSITORIES=${EXTRA_REPOSITORIES}
OVS_SERVERS=${OVS_SERVERS}

case ${SEGMENTATION_TYPE} in
     gre)
        ETH2=${ETH2:-fuelweb_admin,management,storage}
        ETH3=${ETH3:-private}
          ;;
     vlan)
        ETH2=${ETH2:-fuelweb_admin,management,storage}
        ETH3=${ETH3:-private}
          ;;
     tun)
        ETH2=${ETH2:-fuelweb_admin,management,storage}
        ETH3=${ETH3:-private}
          ;;
esac

case ${ENV_NUMBER} in
     10)
        ETH0_CNT=${ETH0_CNT:-fuelweb_admin,management,storage}
        ETH1_CNT=${ETH1_CNT}
        ETH2_CNT=${ETH2_CNT}
        ETH3_CNT=${ETH3_CNT:-private}
        ETH4_CNT=${ETH4_CNT:-public}
        ;;
     *)
        ETH0_CNT=${ETH0}
        ETH1_CNT=${ETH1}
        ETH2_CNT=${ETH2}
        ETH3_CNT=${ETH3}
        ETH4_CNT=${ETH4_CNT}
        ;;
esac


if [ -z "${WORKSPACE}"  ]; then
   echo "\$WORKSPACE must be set"
   exit 1
fi

# Retreave fuel build string:
FUEL_BUILD_NUMBER=`${SSH_CMD} cat /root/FUEL_BUILD_NUMBER || true`

if [ -z "${FUEL_BUILD_NUMBER}" ] ; then
    source ${WORKSPACE}/helpers/fuel_version.sh
    BN_FILE=$(mktemp -u)
    echo ${FUEL_BUILD_NUMBER} > ${BN_FILE}
    ${SCP_CMD} ${BN_FILE} ${SSH_USER}@${FUEL_IP}:/root/FUEL_BUILD_NUMBER
    rm -f ${BN_FILE}
fi

if [ -z "${FUEL_BUILD_NUMBER}" ] ; then
    echo "Can't find build number"
    exit 1
fi

#Create information for run tests script
OS_FILE=$(mktemp -u)
echo ${MAIN_OS} > ${OS_FILE}
${SCP_CMD} ${OS_FILE} ${SSH_USER}@${FUEL_IP}:/root/MAIN_OS
rm -f ${OS_FILE}

CLUSTER_NAME="Build-${FUEL_BUILD_NUMBER}"

cat << EOF > cluster.cfg

[interfaces]
eth0=${ETH0}
eth1=${ETH1}
eth2=${ETH2}
eth3=${ETH3}
[interfaces_controller]
eth0=${ETH0_CNT}
eth1=${ETH1_CNT}
eth2=${ETH2_CNT}
eth3=${ETH3_CNT}
eth4=${ETH4_CNT}
[env]
node_add=${NODE_ADD}
node_max=${NODE_MAX}
power_on_delay=${POWER_ON_DELAY}
env_number=${ENV_NUMBER}
delete_env=${DELETE_ENV}
configure_only=${CONFIGURE_ONLY}
configure_switches=${CONFIGURE_SWITCHES}
fuel_ip=${FUEL_IP}
[cluster]
env_name=${CLUSTER_NAME}
virt_type=${HYPERVISOR}
config_mode=${MODE}
operating_system=${MAIN_OS}
release_name=${RELEASE_NAME}
provision_method=${PROVISION_METHOD}
net_provider=${NETWORK_PROVIDER}
net_segment_type=${SEGMENTATION_TYPE}
cidr=${CIDR}
public_range=${PUBLIC_RANGE}
management_network=${MANAGEMENT_NETWORK}
storage_network=${STORAGE_NETWORK}
private_network=${PRIVATE_NETWORK}
gateway=${GATEWAY}
management_vlan=${MANAGEMENT_VLAN}
public_vlan=${PUBLIC_VLAN}
storage_vlan=${STORAGE_VLAN}
nn_floating_vlan=${FLOATING_VLAN}
floating_vlan_range=${FLOATING_VLAN_RANGE}
floating_range=${FLOATING_RANGE}
node_count=${NODE_COUNT}
controller_count=${CONTROLLER_COUNT}
compute_count=${COMPUTE_COUNT}
ceph_count=${CEPH_COUNT}
volumes_ceph=${VOLUMES_CEPH}
volumes_lvm=${VOLUMES_LVM}
images_ceph=${IMAGES_CEPH}
ephemeral_ceph=${EPHEMERAL_CEPH}
objects_ceph=${OBJECTS_CEPH}
ceilometer=${CEILOMETER}
debug=${DEBUG}
auto_assign_floating_ip=false
nova_quota=${NOVA_QUOTA}
sahara=${SAHARA}
murano=${MURANO}
network_verification=${NETWORK_VERIFICATION}
lma=${LMA}
lab_name=${LAB_NAME}
dvr_enable=${DVR_ENABLE}
ssl_enable=${SSL_ENABLE}
tls_enable=${TLS_ENABLE}
controller_mac_list=${CONTROLLER_MAC_LIST}
extra_repositories=${EXTRA_REPOSITORIES}
# If UBUNTU_REPOSITORY="None" then the repo will not be set (see nailgun.py)
ubuntu_repository=${UBUNTU_REPOSITORY}
influxdb_server=${INFLUXDB_SERVER}
elasticsearch_server=${ELASTICSEARCH_SERVER}
EOF



${SCP_CMD} cluster.cfg ${SSH_USER}@${FUEL_IP}:/root/

rm -rf .venv
virtualenv .venv

#Get private repo and prepare configs
eval `ssh-agent -s`
ssh-add ~/.ssh/${GIT_PRIVATE_KEY}
rm -rf ./mos-private
git clone ${GIT_PRIVATE}
cd ./mos-private
git checkout ${GIT_PRIVATE_BRANCH}
cd -
mv -f ./mos-private/lab-scripts/labs-db.csv ./etc/
mv -f ./mos-private/etc/env-${LAB_NAME}.conf ./etc/env.conf
rm -rf ./mos-private
kill ${SSH_AGENT_PID}
cat cluster.cfg >> etc/env.conf

if [ "$LMA" = "true" ]; then
test "${LMA_VERSION}" = "last_stable" && LMA_VERSION='git branch -r | grep stable | sort -n | tail -1' || LMA_VERSION="echo $LMA_VERSION"
cat > /tmp/lma_install.sh << EOF
      set -xe
      echo "Note! Removal of plugin will fail if it's enabled for any cluster."
      echo "If next commands will fail please login to Fuel dashboard and remove the cluster manually, then restart the job."
			INFLUXDB_GRAFANA_VERSION=${INFLUXDB_GRAFANA_VERSION}
			LMA_COLLECTOR_VERSION=${LMA_COLLECTOR_VERSION}
			ELASTICSEARCH_KIBANA_VERSION=${ELASTICSEARCH_KIBANA_VERSION}
      PLUGINS=(\$(fuel plugins list | tail -n +3 | awk '{print \$3}'))
      VERSIONS=(\$(fuel plugins list | tail -n +3 | awk '{print \$5}'))
      for ((i = 0; i < \${#PLUGINS[@]}; i++))
      do
        if [[ \${PLUGINS[\$i]} -eq "influxdb_grafana" || \${PLUGINS[\$i]} -eq "lma_collector" || \${PLUGINS[\$i]} -eq "elasticsearch_kibana" ]]
        then
          fuel plugins --remove \${PLUGINS[i]}==\${VERSIONS[i]}
        fi
      done
      yum install -y createrepo rpm dpkg-devel dpkg-dev rpm-build git python-pip
      pip install fuel-plugin-builder
      cd /tmp
      rm -rf fuel-plugin-influxdb-grafana
      git clone git://git.openstack.org/openstack/fuel-plugin-influxdb-grafana.git || :
      cd fuel-plugin-influxdb-grafana/
      if [ "\${INFLUXDB_GRAFANA_VERSION}" == "" ]
      then
        INFLUXDB_GRAFANA_VERSION=\$($LMA_VERSION)
      fi
      if [ "\$(echo \${INFLUXDB_GRAFANA_VERSION} | grep -Eo 'refs/changes/+')" != "" ]
      then
        git fetch https://git.openstack.org/openstack/fuel-plugin-influxdb-grafana ${INFLUXDB_GRAFANA_VERSION} && git checkout FETCH_HEAD
      else
        git checkout \${INFLUXDB_GRAFANA_VERSION}
      fi
      cd ../
      rm -rf fuel-plugin-lma-collector
      git clone git://git.openstack.org/openstack/fuel-plugin-lma-collector.git || :
      cd fuel-plugin-lma-collector
      if [ "\${LMA_COLLECTOR_VERSION}" == "" ]
      then
        LMA_COLLECTOR_VERSION=\$($LMA_VERSION)
      fi
      if [ "\$(echo \${LMA_COLLECTOR_VERSION} | grep -Eo 'refs/changes/+')" != "" ]
      then
        git fetch https://git.openstack.org/openstack/fuel-plugin-lma-collector ${LMA_COLLECTOR_VERSION} && git checkout FETCH_HEAD
      else
        git checkout \${LMA_COLLECTOR_VERSION}
      fi
      cd ../
      rm -rf fuel-plugin-elasticsearch-kibana
      git clone git://git.openstack.org/openstack/fuel-plugin-elasticsearch-kibana.git || :
      cd fuel-plugin-elasticsearch-kibana
      if [ "\${ELASTICSEARCH_KIBANA_VERSION}" == "" ]
      then
        ELASTICSEARCH_KIBANA_VERSION=\$($LMA_VERSION)
      fi
      if [ "\$(echo \${ELASTICSEARCH_KIBANA_VERSION} | grep -Eo 'refs/changes/+')" != "" ]
      then
        git fetch https://git.openstack.org/openstack/fuel-plugin-elasticsearch-kibana ${ELASTICSEARCH_KIBANA_VERSION} && git checkout FETCH_HEAD
      else
        git checkout \${ELASTICSEARCH_KIBANA_VERSION}
      fi
      cd ../
      fpb --build fuel-plugin-influxdb-grafana/
      fpb --build fuel-plugin-lma-collector/
      fpb --build fuel-plugin-elasticsearch-kibana/
      cd fuel-plugin-influxdb-grafana/
      sed -i 's/\"refresh_on_load\": false/\"refresh_on_load\": true/g' deployment_scripts/puppet/modules/lma_monitoring_analytics/templates/grafana_dashboards/*.json
      fuel plugins --install *.rpm
      cd -
      cd fuel-plugin-lma-collector/
      fuel plugins --install *.rpm
      cd -
      cd fuel-plugin-elasticsearch-kibana/
      fuel plugins --install *.rpm
      cd -
EOF
  ${SSH_CMD} rm -rf /tmp/lma_install.sh
  ${SCP_CMD} /tmp/lma_install.sh ${SSH_USER}@${FUEL_IP}:/tmp/
  ${SSH_CMD} chmod 755 /tmp/lma_install.sh
  ${SSH_CMD} /tmp/lma_install.sh
fi

${WDIR}/.venv/bin/pip install -r ././../../requirements.txt
cd ././../../
${WDIR}/.venv/bin/python setup.py install
${WDIR}/.venv/bin/python ${WDIR}/deploy_cluster.py

cd -
rm -rf ./mos-private

#if [ "$LMA" != "true" ]; then
#    $RSYNC_CMD -rlt "${WDIR}/collectd_playbook/" ${SSH_USER}@${FUEL_IP}:.collectd_ansible/playbook/
#    ${SSH_CMD} < "${WDIR}/deploy_collectd.sh"
#fi
