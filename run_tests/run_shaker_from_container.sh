#!/bin/bash -ex

: ${ENV:?}
: ${SHAKER_IMAGE_NAME:?}
: ${SERVER_IP:?}

: ${GERRIT_USER:=mos-scale-jenkins}
: ${GERRIT_KEY:=mos-scale-jenkins}
: ${GIT_SCENARIOS_REF:=origin/master}
: ${VOLUMES_DIR:=/var/lib/volumes/test_results}
: ${GIT_SCENARIOS_REF:=origin/master}

GIT_SCENARIOS="ssh://${GERRIT_USER}@gerrit.mirantis.com:29418/mos-scale/mos-scenarios"
LAST_IP=$((60+${ENV}))
FUEL_IP_FOR_ACCESS="172.20.8.${LAST_IP}"

# Which scenarios need to run.
# Path relatively to SCENARIOS_PATH with scenario files
# Can be: string of dir and files separated by space.
: ${SCENARIOS_NAMES:-shaker-scenarios}

TIME="UTC-$(date +%Y-%m-%d-%H-%M-%S)"
SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
SSH_PASSWORD="r00tme"
SSH_CMD="sshpass -p ${SSH_PASSWORD} ssh -t -t ${SSH_OPTS} root@${FUEL_IP_FOR_ACCESS}"
SCP_CMD="sshpass -p ${SSH_PASSWORD} scp ${SSH_OPTS} "
FUEL_VERSION=`${SSH_CMD} cat /etc/fuel_release | dos2unix`
FUEL_BUILD=`${SSH_CMD} cat /etc/fuel_build_id | dos2unix`
FUEL_RELEASE_ID=`${SSH_CMD} fuel env | grep operational | awk -F"|" '{print $4}' | sed s/" "//g | head -1 | dos2unix`
MAIN_OS=`${SSH_CMD} fuel rel | grep -w ^${FUEL_RELEASE_ID} | awk -F"|" '{print $4}' | sed s/" "//g | tr [:upper:] [:lower:]`
TEST_DIR="${VOLUMES_DIR}/build_${FUEL_VERSION}-${FUEL_BUILD}/${BUILD_TAG}-${MAIN_OS}-${TIME}"

ENV_ID=`${SSH_CMD} fuel env | grep operational | awk -F"|" '{print $1}' | sed s/" "//g | head -1`
${SCP_CMD} root@${FUEL_IP_FOR_ACCESS}:/etc/fuel/cluster/${ENV_ID}/astute.yaml ./
OS_USERNAME=`python helpers/astute_yaml_parser.py user`
OS_TENANT_NAME=`python helpers/astute_yaml_parser.py tenant`
OS_PASSWORD=`python helpers/astute_yaml_parser.py password`
MGMT_VIP=`python helpers/astute_yaml_parser.py mgmt_vip`
OS_AUTH_URL="http://${MGMT_VIP}:5000/v2.0"

# Calculate SERVER_ENDPOINT for shaker runner
RANDOM_PORT=`python -c 'import socket; s=socket.socket(); s.bind(("", 0)); print(s.getsockname()[1]); s.close()'`
SERVER_ENDPOINT=${SERVER_IP}:${RANDOM_PORT}

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

cat << EOF > shaker-${ENV}.yaml
apiVersion: v1
kind: Pod
metadata:
  name: shaker-${ENV}
  labels:
    name: shaker-${ENV}
spec:
  containers:
  - image: ${SHAKER_IMAGE_NAME}
    name: shaker-${ENV}
    ports:
    - containerPort: ${RANDOM_PORT}
    env:
    - name: OS_AUTH_URL
      value: ${OS_AUTH_URL}
    - name: OS_PASSWORD
      value: ${OS_PASSWORD}
    - name: OS_USERNAME
      value: ${OS_USERNAME}
    - name: OS_TENANT_NAME
      value: ${OS_TENANT_NAME}
    - name: SERVER_ENDPOINT
      value: ${SERVER_ENDPOINT}
    - name: SCENARIOS_NAMES
      value: ${SCENARIOS_NAMES}
    volumeMounts:
    - mountPath: /data/shaker/mos_scenarios
      name: mos-scenarios
    - mountPath: /data/shaker/artifacts
      name: artifacts-dir
  restartPolicy: Never
  volumes:
  - hostPath:
      path: ${TEST_DIR}/mos-scenarios
    name: mos-scenarios
  - hostPath:
      path: ${TEST_DIR}/logs
    name: artifacts-dir
---
apiVersion: v1
kind: Service
metadata:
  name: shaker-service-${ENV}
spec:
  selector:
    name: shaker-${ENV}
  ports:
  - port: ${RANDOM_PORT}
    targetPort: ${RANDOM_PORT}
  externalIPs:
  - ${SERVER_IP}
EOF

kubectl delete pod shaker-${ENV} || true
kubectl delete service shaker-service-${ENV} || true
kubectl create -f shaker-${ENV}.yaml

while [ "`kubectl get pods -a | grep shaker-${ENV} | awk '{print $3}'`" != "Running" ]
do
  sleep 1
done

while [ "`kubectl get pods -a | grep shaker-${ENV} | awk '{print $3}'`" == "Running" ]
do
  set +e
  kubectl attach shaker-${ENV}
  set -e
done
kubectl delete pod shaker-${ENV} || true
kubectl delete service shaker-service-${ENV} || true

TIME="$(date +%Y-%m-%d-%H-%M-%S)"
mv "${TEST_DIR}" "${TEST_DIR}-${TIME}"
find ${TEST_DIR}-${TIME}/logs -maxdepth 1 -type f ! -name '*.log' -exec mv {} ${TEST_DIR}-${TIME} \;
cp ${TEST_DIR}-${TIME}/*.subunit ./
