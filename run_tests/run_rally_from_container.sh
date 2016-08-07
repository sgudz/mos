#!/bin/bash -ex

ENV=${ENV:?}
HTTP_SERVER_WITH_GLANCE_IMAGES=${HTTP_SERVER_WITH_GLANCE_IMAGES:?}
LAST_IP=$((60+${ENV}))
FUEL_IP_FOR_ACCESS="172.20.8.${LAST_IP}"
GERRIT_USER=${GERRIT_USER:-mos-scale-jenkins}
GERRIT_KEY=${GERRIT_KEY:-mos-scale-jenkins}
GIT_SCENARIOS_REF=${GIT_SCENARIOS_REF:-origin/master}
GIT_SCENARIOS="ssh://${GERRIT_USER}@gerrit.mirantis.com:29418/mos-scale/mos-scenarios"
: ${RALLY_IMAGE_NAME:?}
: ${LOAD:=1}
: ${RST_REPORT_TYPE:=""}
# Influxdb connection string for export data plugin from rally
# to influxdb/grafana
: ${INFLUXDB_CONNECTION:?}

# Which scenarios need to run.
# Path relatively to SCENARIOS_PATH with scenario files
# Can be: string of dir and files separated by space.
: ${SCENARIOS_NAMES:-performance-rally-scenarios}

VOLUMES_DIR="/var/lib/volumes/test_results"
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_PASSWORD="r00tme"
SSH_CMD="sshpass -p ${SSH_PASSWORD} ssh -t -t ${SSH_OPTS} root@${FUEL_IP_FOR_ACCESS}"
SCP_CMD="sshpass -p ${SSH_PASSWORD} scp ${SSH_OPTS} "
BUILD_TAG=${BUILD_TAG}
TIME="UTC-$(date +%Y-%m-%d-%H-%M-%S)"
FUEL_VERSION=`${SSH_CMD} cat /etc/fuel_release | dos2unix`
FUEL_BUILD=`${SSH_CMD} cat /etc/fuel_build_id | dos2unix`
ENV_ID=`${SSH_CMD} fuel env | grep operational | awk -F"|" '{print $1}' | sed s/" "//g | head -1`
FUEL_RELEASE_ID=`${SSH_CMD} fuel env | grep operational | awk -F"|" '{print $4}' | sed s/" "//g | head -1 | dos2unix`
MAIN_OS=`${SSH_CMD} fuel rel | grep -w ^${FUEL_RELEASE_ID} | awk -F"|" '{print $4}' | sed s/" "//g | tr [:upper:] [:lower:]`
TEST_DIR="${VOLUMES_DIR}/build_${FUEL_VERSION}-${FUEL_BUILD}/${BUILD_TAG}-${MAIN_OS}-${TIME}"
mkdir -p ${TEST_DIR}/logs

#Get scenarios
eval `ssh-agent -s`
ssh-add ~/.ssh/${GERRIT_KEY}
rm -rf ./mos-scenarios
git clone ${GIT_SCENARIOS}
cd ./mos-scenarios
git fetch ${GIT_SCENARIOS} ${GIT_SCENARIOS_REF} && git checkout FETCH_HEAD
cd -
rm -rf mos-scenarios/.git
kill ${SSH_AGENT_PID}
cp -r mos-scenarios ${TEST_DIR}/

${SCP_CMD} root@${FUEL_IP_FOR_ACCESS}:/etc/fuel/cluster/${ENV_ID}/astute.yaml ./
${SCP_CMD} root@${FUEL_IP_FOR_ACCESS}:/root/.ssh/id_rsa ./
MGMT_VIP=`python helpers/astute_yaml_parser.py mgmt_vip`
OS_USER=`python helpers/astute_yaml_parser.py user`
OS_TENANT=`python helpers/astute_yaml_parser.py tenant`
OS_PASSWORD=`python helpers/astute_yaml_parser.py password`
INFLUXDB_ADDRESS=`python helpers/astute_yaml_parser.py influxdb_address`
LMA_LABEL=`python helpers/astute_yaml_parser.py lma_label`
OS_EXT_NET=`python helpers/astute_yaml_parser.py ext_net`
if [ "${LIGHT}" == true ]
then
  COMPUTES_COUNT=5
  LOAD=1
else
  COMPUTES_COUNT=`python helpers/astute_yaml_parser.py computes_count`
fi

cat << EOF > ${TEST_DIR}/rally_deployment.json
{
    "admin": {
        "password": "${OS_PASSWORD}",
        "tenant_name": "${OS_TENANT}",
        "username": "${OS_USER}"
    },
    "auth_url": "http://${MGMT_VIP}:5000/v2.0",
    "region_name": "RegionOne",
    "type": "ExistingCloud",
    "endpoint_type": "internal",
    "admin_port": 35357,
    "https_insecure": true,
    "fuel_env": {
        "environment_label": "${LMA_LABEL}",
        "environment_id": "${ENV_ID}",
        "mos_iso": "${FUEL_VERSION}-${FUEL_BUILD}",
        "jenkins_build_number": ${BUILD_TAG}
    }
}
EOF

cat << EOF > ${TEST_DIR}/job-params.yaml
---
    concurrency: $((5*${LOAD}))
    compute: ${COMPUTES_COUNT}
    start_cidr: "1.0.0.0/16"
    current_path: "/home/rally/rally-scenarios/heat/"
    floating_ip_amount: 800
    floating_net: "admin_floating_net"
    vlan_amount: 1025
    gre_enabled: false
    http_server_with_glance_images: "${HTTP_SERVER_WITH_GLANCE_IMAGES}"
EOF

RALLY_DEPLYMENT_NAME=${BUILD_TAG}

cat << EOF > rally-${ENV}.yaml
apiVersion: v1
kind: Pod
metadata:
  name: rally-${ENV}
spec:
  containers:
  - image: ${RALLY_IMAGE_NAME}
    name: rally-${ENV}
    env:
    - name: DEPLOYMENT_NAME
      value: ${RALLY_DEPLYMENT_NAME}
    - name: INFLUXDB_CONNECTION
      value: ${INFLUXDB_CONNECTION}
    - name: SCENARIOS_NAMES
      value: ${SCENARIOS_NAMES}
    - name: ASTUTE_YAML_FILE
      value: /data/rally/astute.yaml
    - name: RST_REPORT_TYPE
      value: ${RST_REPORT_TYPE}
    volumeMounts:
      - mountPath: /data/rally/job-params.yaml
        name: job-params
      - mountPath: /data/rally/mos_scenarios
        name: mos-scenarios
      - mountPath: /data/rally/deployment.json
        name: deployment-json
      - mountPath: /data/rally/artifacts
        name: artifacts-dir
      - mountPath: /data/rally/astute.yaml
        name: astute-yaml
      - mountPath: /root/.ssh/id_rsa
        name: id-rsa
  restartPolicy: Never
  volumes:
    - hostPath:
        path: ${TEST_DIR}/job-params.yaml
      name: job-params
    - hostPath:
        path: ${TEST_DIR}/mos-scenarios
      name: mos-scenarios
    - hostPath:
        path: ${TEST_DIR}/rally_deployment.json
      name: deployment-json
    - hostPath:
        path: ${TEST_DIR}/logs
      name: artifacts-dir
    - hostPath:
        path: $(pwd)/astute.yaml
      name: astute-yaml
    - hostPath:
        path: $(pwd)/id_rsa
      name: id-rsa
EOF

#sudo chown -R 65500 ${TEST_DIR}

kubectl delete pod rally-${ENV} || true
kubectl create -f rally-${ENV}.yaml

while [ "`kubectl get pods -a | grep rally-${ENV} | awk '{print $3}'`" != "Running" ]
do
  sleep 1
done

while [ "`kubectl get pods -a | grep rally-${ENV} | awk '{print $3}'`" == "Running" ]
do
  set +e
  kubectl attach rally-${ENV}
  set -e
done
kubectl delete pod rally-${ENV}

TIME="$(date +%Y-%m-%d-%H-%M-%S)"
mv "${TEST_DIR}" "${TEST_DIR}-${TIME}"
find ${TEST_DIR}-${TIME}/logs -maxdepth 1 -type f ! -name '*.log' -exec mv {} ${TEST_DIR}-${TIME} \;
cp ${TEST_DIR}-${TIME}/rally_report.xml ./
mv ${TEST_DIR}-${TIME}/report.html /var/lib/volumes/comparasion/index.html
