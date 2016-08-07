#!/bin/bash

TOP_DIR=$(cd $(dirname "$0") && pwd)
DEST=${DEST:-/opt/stack}

cd ${DEST}/elk/dashboard
python -m SimpleHTTPServer 10000 &>/dev/null &

cd ${DEST}/logstash
./bin/logstash -f ${DEST}/elk/logstash.conf
