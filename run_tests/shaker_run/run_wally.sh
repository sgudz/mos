#!/bin/bash

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
echo "latency_10iops =" $LATENCY_10_IOPS >> env.conf
echo "latency_30iops =" $LATENCY_30_IOPS >> env.conf
echo "latency_100iops =" $LATENCY_100_IOPS >> env.conf

python addresult_wally.py
