#!/usr/bin/env bash -x

install_elk(){
    message "Installing ELK into ${DEST}"
    cd ${DEST}
    cp -r ${TOP_DIR}/elk ${DEST}/

    LOGSTASH_DISTRO="logstash-1.4.2"
    wget http://download.elasticsearch.org/logstash/logstash/${LOGSTASH_DISTRO}.tar.gz
    tar xzf ${LOGSTASH_DISTRO}.tar.gz
    rm ${LOGSTASH_DISTRO}.tar.gz
    rm -rf logstash
    mv ${LOGSTASH_DISTRO} logstash

    ELASTIC_DISTRO="elasticsearch-1.4.2"
    wget http://download.elasticsearch.org/elasticsearch/elasticsearch/${ELASTIC_DISTRO}.tar.gz
    tar xzf ${ELASTIC_DISTRO}.tar.gz
    rm ${ELASTIC_DISTRO}.tar.gz
    rm -rf elasticsearch
    mv ${ELASTIC_DISTRO} elasticsearch
    mkdir /var/lib/elk || :
    echo "http.cors.enabled: true" >> elasticsearch/config/elasticsearch.yml
    echo "path.data: /var/lib/elk" >> elasticsearch/config/elasticsearch.yml
    echo "path.logs: /var/log/elk" >> elasticsearch/config/elasticsearch.yml

    KIBANA_DISTRO="kibana-3.1.2"
    wget http://download.elasticsearch.org/kibana/kibana/${KIBANA_DISTRO}.tar.gz
    tar xzf ${KIBANA_DISTRO}.tar.gz
    rm -rf elk/dashboard/kibana
    mv ${KIBANA_DISTRO} elk/dashboard/kibana
    rm ${KIBANA_DISTRO}.tar.gz
    mv elk/dashboard/kibana/app/dashboards/default.json elk/dashboard/kibana/app/dashboards/default.json.bak
    cp elk/dashboard/kibana/app/dashboards/logstash.json elk/dashboard/kibana/app/dashboards/default.json
    mv elk/dashboard/kibana/config.js elk/dashboard/kibana/config.js.template
    cat elk/dashboard/kibana/config.js.template | \
        sed 's|elasticsearch:.*|elasticsearch: "http://" + window.location.hostname + ":9200",|' > elk/dashboard/kibana/config.js

    rm -rf /var/log/elk || true
    mkdir -p /var/log/elk
    touch /var/log/elk/elasticsearch.log
    touch /var/log/elk/logstash.log
    chmod -R o+w /var/log/elk
}

run_elk() {
    cd ${DEST}/elk/dashboard
    python -m SimpleHTTPServer 10000 &>/dev/null &

    if [ -f /var/log/elk/elasticsearch.log ]; then
        fuser -k /var/log/elk/elasticsearch.log || true
    fi
    cd ${DEST}/elasticsearch
    ./bin/elasticsearch &>/var/log/elk/elasticsearch.log &

    if [ -f /var/log/elk/logstash.log ]; then
        fuser -k /var/log/elk/logstash.log || true
    fi
    cd ${DEST}/logstash
    ./bin/logstash -f ${DEST}/elk/logstash.conf &>/var/log/elk/logstash.log &

    # sleep while processes start up
    sleep 5
}

main() {
    install_elk
    #run_elk
}

main "$@"
