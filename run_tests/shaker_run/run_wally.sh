#!/bin/bash
export SSH_OPTS='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=quiet'
COMPUTE_IP=`fuel node | grep compute | awk -F "|" '{print $5}' | sed 's/ //g' | head -n 1`
REMOTE_SCRIPT=`ssh $COMPUTE_IP "mktemp"`
ssh ${SSH_OPTS} $COMPUTE_IP "cat > ${REMOTE_SCRIPT}" <<EOF
set -x
printf 'deb http://ua.archive.ubuntu.com/ubuntu/ trusty universe' > /etc/apt/sources.list
apt-get update
apt-get -y install git python-pip python-dev libxft-dev libblas-dev liblapack-dev libatlas-base-dev gfortran python-numpy python-scipy python-matplotlib ipython ipython-notebook python-pandas python-sympy python-nose libblas3gf liblapack3gf libgfortran3 gfortran-4.6 gfortran libatlas3gf-base libfreetype6 libpng12-dev pkg-config swift libxml2-dev libxslt1-dev zlib1g-dev
pip install --upgrade pip
pip install paramiko pbr vcversioner pyOpenSSL texttable sshtunnel lxml pandas
git clone https://github.com/Mirantis/disk_perf_test_tool.git
cd disk_perf_test_tool/
pip install -r requirements.txt
python -m wally test "test2" test1.yaml > file.tmp
EOF
ssh ${SSH_OPTS} $COMPUTE_IP "bash ${REMOTE_SCRIPT}"

#REP_DIR=`ssh ${SSH_OPTS} $COMPUTE_IP cat disk_perf_test_tool/file.tmp | grep -E "All info would be stored into /var/" | grep -Po "/var/.*"`
scp ${SSH_OPTS} $COMPUTE_IP:/var/wally_results/*/ceph_report.html /root/

READ_16MIB_MEDIAN=$(cat ceph_report.html | grep -A1 "Read" | awk '(NR == 5)' | grep -Eo "[0-9]*" | awk '(NR == 1)')
READ_16MIB_STDEV=$(cat ceph_report.html | grep -A1 "Read" | awk '(NR == 5)' | grep -Eo "[0-9]*" | awk '(NR == 4)')
READ_4KIB_MEDIAN=$(cat ceph_report.html | grep -A1 "Read" | awk '(NR == 2)' | grep -Eo "[0-9]*" | awk '(NR == 1)')
READ_4KIB_STDEV=$(cat ceph_report.html | grep -A1 "Read" | awk '(NR == 2)' | grep -Eo "[0-9]*" | awk '(NR == 4)')

WRITE_16MIB_MEDIAN=$(cat ceph_report.html | grep -A1 "Write" | awk '(NR == 5)' | grep -Eo "[0-9]*" | awk '(NR == 1)')
WRITE_16MIB_STDEV=$(cat ceph_report.html | grep -A1 "Write" | awk '(NR == 5)' | grep -Eo "[0-9]*" | awk '(NR == 4)')
WRITE_4KIB_MEDIAN=$(cat ceph_report.html | grep -A1 "Write" | awk '(NR == 2)' | grep -Eo "[0-9]*" | awk '(NR == 1)')
WRITE_4KIB_STDEV=$(cat ceph_report.html | grep -A1 "Write" | awk '(NR == 2)' | grep -Eo "[0-9]*" | awk '(NR == 4)')

LATENCY_10_IOPS=$(cat ceph_report.html | grep -PA1 "align\=\"right\"\>10" | awk '(NR == 2)' | grep -Eo "[0-9]*")
LATENCY_30_IOPS=$(cat ceph_report.html | grep -PA1 "align\=\"right\"\>30" | awk '(NR == 2)' | grep -Eo "[0-9]*")
LATENCY_100_IOPS=$(cat ceph_report.html | grep -PA1 "align\=\"right\"\>100" | awk '(NR == 2)' | grep -Eo "[0-9]*")

echo "read_16mib_median =" $READ_16MIB_MEDIAN >> env.conf
echo "read_16mib_stdev =" $READ_16MIB_STDEV >> env.conf
echo "read_4kib_median =" $READ_4KIB_MEDIAN >> env.conf
echo "read_4kib_stdev =" $READ_4KIB_STDEV >> env.conf
echo "write_16mib_median =" $WRITE_16MIB_MEDIAN >> env.conf
echo "write_16mib_stdev =" $WRITE_16MIB_STDEV >> env.conf
echo "write_4kib_median =" $WRITE_4KIB_MEDIAN >> env.conf
echo "write_4kib_stdev =" $WRITE_4KIB_STDEV >> env.conf
echo "latency_10_ms =" $LATENCY_10_IOPS >> env.conf
echo "latency_30_ms =" $LATENCY_30_IOPS >> env.conf
echo "latency_100_ms =" $LATENCY_100_IOPS >> env.conf

python addresult_wally.py
