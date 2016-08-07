#!/bin/bash

SERVER_NAME=`hostname`
STORE_RESULTS_TO_FOLDER=/root
TMP_DIR=/tmp/collect_server_info_workdir
SERVER_DIR=${TMP_DIR:?}/${SERVER_NAME}
COMMANDS_RESULTS_DIR=${SERVER_DIR:?}/commands

if [ ! -d ${SERVER_DIR} ]
then
  rm -rf ${SERVER_DIR}
  mkdir -p ${SERVER_DIR}
fi

install_requirements ()
{
  apt-get update
  apt-get -y install lsscsi
}

perform_commands ()
{
  if [ ! -d ${COMMANDS_RESULTS_DIR} ]
  then
    mkdir -p ${COMMANDS_RESULTS_DIR}
  fi
  uname -a > ${COMMANDS_RESULTS_DIR}/uname.txt
  ip a > ${COMMANDS_RESULTS_DIR}/ip_a.txt
  ip ro > ${COMMANDS_RESULTS_DIR}/ip_ro.txt
  df -h > ${COMMANDS_RESULTS_DIR}/df_-h.txt
  cat /proc/mounts > ${COMMANDS_RESULTS_DIR}/mounts.txt
  ss -anp > ${COMMANDS_RESULTS_DIR}/ss_-anp.txt
  sysctl -a > ${COMMANDS_RESULTS_DIR}/sysctl_-a.txt
  dpkg -l > ${COMMANDS_RESULTS_DIR}/dpkg_-l.txt
  cat /proc/meminfo > ${COMMANDS_RESULTS_DIR}/meminfo.txt
  tail -27 /proc/cpuinfo > ${COMMANDS_RESULTS_DIR}/tail_-27_proc_cpuinfo.txt
  lspci > ${COMMANDS_RESULTS_DIR}/lspci.txt
  lsscsi > ${COMMANDS_RESULTS_DIR}/lsscsi.txt
  cat /proc/cmdline > ${COMMANDS_RESULTS_DIR}/cmdline.txt
  cat /proc/softirqs > ${COMMANDS_RESULTS_DIR}/softirqs.txt
  dmesg > ${COMMANDS_RESULTS_DIR}/dmesg.txt
}

copy_etc()
{
  cp -r /etc/ ${SERVER_DIR}/
}
create_archive()
{
  tar zcvf ${STORE_RESULTS_TO_FOLDER}/server_description.tar.gz -C ${TMP_DIR} .
  echo "Archive with collected server info has been created and stored here: ${STORE_RESULTS_TO_FOLDER}/server_description_of_${SERVER_NAME}.tar.gz"
}

main()
{
  install_requirements
  perform_commands
  copy_etc
  create_archive
}

main
