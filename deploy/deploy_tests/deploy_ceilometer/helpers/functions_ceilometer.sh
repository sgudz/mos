#!/usr/bin/env bash -x

packages_install() {
    distro=`ssh $1 "cat /etc/*release | grep -Eo \"Ubuntu|CentOS\"" | head -n 1`
if [ ! -z "$distro" ]; then
    if [[ "$distro" == "CentOS" ]]; then ssh $1 "yum install $2 -y";
    elif [[ "$distro" == "Ubuntu" ]]; then ssh $1 "apt-get install $2 -y";
    else error "Distributor on controllers is unknown";
    fi
else error "Distributor on controllers not determined";
fi
}

available_ceilometer() {
if [ ! -z "`fuel node | grep mongo`" ]; then

    # Create massive with controllers
    index=0
    for i in `fuel node | grep controller | awk '{print $1}'`; do controllers[$index]="node-$i" index=$(($index+1)); done
    index=0
    for i in `fuel node | grep mongo | awk '{print $1}'`; do mongos[$index]="node-$i" index=$(($index+1)); done

    return 1;
    else message "Mongo role not found in controllers. Logging not run."; return 0;
fi
}

create_and_run_ceilo_logs_on_controllers() {
    packages_install $1 "dstat vim screen"
    file_size_limitation $1
    ssh $1 <<EOF
    screen -dmS psstatlogceilo /bin/bash -c "while true ;
        do date +%s >> /tmp/ceilometer_logs/$1-ceilo-psstat.log;
        ps -eo %cpu,%mem,vsize,size,comm | grep ceilo >> /tmp/ceilometer_logs/$1-ceilo-psstat.log;
        sleep 2;  done"
EOF
}

create_and_run_ceilo_logs_on_mongo_nodes() {
    scp ${TOP_DIR}/mongo_io_script root@$1:/tmp/mongo_io_script.py
    packages_install $1 "vim screen python-pymongo dstat"
    mongourl=`ssh ${controllers[0]} "cat /etc/ceilometer/ceilometer.conf | grep "^[^#].*mongo" | sed 's/connection=//'"`
    file_size_limitation $1
    ssh $1 <<EOF
    screen -dmS psstatlogmongo /bin/bash -c "while true ;
        do date +%s >> /tmp/ceilometer_logs/$1-mongo-psstat.log;
        ps -eo %cpu,%mem,vsize,size,comm | grep mongo >> /tmp/ceilometer_logs/$1-mongo-psstat.log;
        sleep 2;  done"
    screen -dmS mongoiolog python /tmp/mongo_io_script.py $mongourl 2 $1
    screen -dmS iostatlog /bin/bash -c "dstat --disk-util 2 >> /tmp/ceilometer_logs/$1-iostat.log"
EOF
}

file_size_limitation() {
    ssh $1 <<EOF
    if [ -d /tmp/ceilometer_logs ]; then rm -rf /tmp/ceilometer_logs/*; else mkdir /tmp/ceilometer_logs; fi
    cd /tmp/ceilometer_logs
    screen -dmS filelimitation /bin/bash -c "while true ;
    do
        for logfile in `ls`; do
            actualsize=$(du --block-size=G $logfile | cut -f 1)
            if [ $actualsize -ge 2 ];
                scrs=`screen -ls | egrep "mongoiolog|psstatlogceilo|psstatlogmongo|iostatlog" | awk {'print $1'}`
                for i in $scrs; do screen -X -S $i quit; done
                screen -X -S filelimitation quit
            fi

        done
    done
    "
EOF
}

run_ceilometer_logs() {

    if available_ceilometer; then return; fi

    for ((a=0; a < ${#controllers[*]}; a++))
    do
        create_and_run_ceilo_logs_on_controllers ${controllers[$a]}
    done

    for ((a=0; a < ${#mongos[*]}; a++))
    do
        create_and_run_ceilo_logs_on_mongo_nodes ${mongos[$a]}
    done
}

stop_ceilometer_screens() {
    scrs=`ssh $1 "screen -ls | egrep \"mongoiolog|psstatlogceilo|psstatlogmongo|iostatlog|filelimitation\"" | awk {'print $1'}`
    for i in $scrs; do ssh $1 "screen -X -S $i quit"; done
}

delete_ceilometer_files() {
    ssh $1 << EOF
    rm /tmp/mongo_io_script.py >> /dev/null
    rm -rf /tmp/ceilometer_logs/
EOF
}

stop_ceilometer_logs() {

    if available_ceilometer; then return; fi

    if [ -d /tmp/ceilometer_logs/ ]; then rm -rf /tmp/ceilometer_logs/; fi
    mkdir /tmp/ceilometer_logs/

    for ((a=0; a < ${#controllers[*]}; a++))
    do
        stop_ceilometer_screens ${controllers[$a]}
        scp ${controllers[$a]}:/tmp/ceilometer_logs/* /tmp/ceilometer_logs/
        delete_ceilometer_files ${controllers[$a]}
    done

    for ((a=0; a < ${#mongos[*]}; a++))

    do
        stop_ceilometer_screens ${mongos[$a]}
        scp ${mongos[$a]}:/tmp/ceilometer_logs/* /tmp/ceilometer_logs/
        delete_ceilometer_files ${mongos[$a]}
    done
}