#!/bin/bash -xe
#
# This script installs development and QA tools for Fuel.
#

set -e

TOP_DIR=$(cd $(dirname "$0") && pwd)
cd ${TOP_DIR}

print_usage() {
    echo "Usage: ${0##*/} [-h]"
    echo "Options:"
    echo "  -h: print this usage message and exit"
}


error() {
    printf "\e[31mError: %s\e[0m\n" "${*}" >&2
    exit 1
}

message() {
    printf "\e[33m%s\e[0m\n" "${1}"
}

check_root() {
    local user=$(/usr/bin/id -u)
    if [ ${user} -ne 0 ]; then
        error "Only the superuser (uid 0) can use this script."
        exit 1
    fi
}

parse_arguments() {
    while getopts ":h" opt; do
        case ${opt} in
            h)
                print_usage
                exit 0
                ;;
            *)
                error "An invalid option has been detected."
                print_usage
                exit 1
        esac
    done
}

init_variables() {
    export USER_NAME=developer
    export USER_HOME=/home/${USER_NAME}
    export DEST=${DEST:-/opt/stack}
    export VIRTUALENV_DIR=${DEST}/.venv
    export SCALE_LAB_UUID=${SCALE_LAB_UUID:-SkyNet}
    export PIP_SECURE_LOCATION="https://bootstrap.pypa.io/get-pip.py"
    export TMP="`dirname \"$0\"`"
    export TMP="`( cd \"${TMP}\" && pwd )`"

    mkdir -p ${DEST}
}

install_system_requirements() {
    message "Enable default CentOS repos"
    yum -y reinstall centos-release  # enable default CentOS repos

    message "Installing system requirements"
    yum -y install bc
    yum -y install git
    yum -y install gcc
    yum -y install zlib-devel
    yum -y install sqlite-devel
    yum -y install readline-devel
    yum -y install bzip2-devel
    yum -y install libgcrypt-devel
    yum -y install openssl-devel
    yum -y install libffi-devel
    yum -y install libxml2-devel
    yum -y install libxslt-devel
    yum -y install screen
    yum -y install java-1.7.0-openjdk.x86_64
    yum -y install postgresql-devel
    yum -y install gcc-c++
    yum -y install freetype-devel libpng-devel
    yum -y install python-devel

    if command -v pg_config 2>&1; then
        message "Pg_config is found"
    else
        message "fix for Error: pg_config executable not found. in pip install -U psycopg2"
        ln -fs /usr/pgsql-9.3/bin/pg_config /usr/bin/pg_config
    fi
}

install_python_27() {
    if command -v python2.7 >/dev/null 2>&1; then
        message "Python 2.7 already installed"
    else
        message "Installing Python 2.7"
        TMP="`mktemp -d`"
        cd ${TMP}
        wget https://www.python.org/ftp/python/2.7.8/Python-2.7.8.tgz
        tar xzf Python-2.7.8.tgz
        cd Python-2.7.8
        ./configure --prefix=/usr/local --enable-unicode=ucs4 --enable-shared LDFLAGS="-Wl,-rpath /usr/local/lib"
        make -j5 altinstall
    fi

    if command -v pip2.7 >/dev/null 2>&1; then
        message "Pip 2.7 already installed"
    else
        message "Installing pip and virtualenv for Python 2.7"
        GETPIPPY_FILE="`mktemp`"
        wget -O ${GETPIPPY_FILE} ${PIP_SECURE_LOCATION}
        python2.7 ${GETPIPPY_FILE}
    fi

    if command -v virtualenv >/dev/null 2>&1; then
        message "Virtualenv already installed"
    else
        message "Installing virtualenv for Python 2.7"
        pip2.7 install -U virtualenv
    fi

    if command -v tox >/dev/null 2>&1; then
        message "Tox already installed"
    else
        message "Installing tox for Python 2.7"
        pip2.7 install -U tox
    fi
}

setup_virtualenv() {
    message "Setup virtualenv in ${VIRTUALENV_DIR}"
    virtualenv -p python2.7 ${VIRTUALENV_DIR}
}

activate_virtualenv() {
    source ${VIRTUALENV_DIR}/bin/activate
}

init_cluster_variables() {
    message "Initializing cluster variables"
    CONTROLLER_HOST_ID="`fuel node | grep controller | awk '{print $1}' | head -1`"
    CONTROLLER_HOST="node-${CONTROLLER_HOST_ID}"
    message "Controller host: ${CONTROLLER_HOST}"

    export FUEL_RELEASE=`fuel --fuel-version 2>&1 | grep -e ^release: | awk '{print $2}'`
    ssh root@${CONTROLLER_HOST} "sed -i -r \"s/export OS_AUTH_URL='([htp:/0-9.]+)'$/export OS_AUTH_URL='\1v2.0\/'/\" openrc"
    export OS_AUTH_URL=`ssh root@${CONTROLLER_HOST} ". openrc; keystone catalog --service identity | grep  internalURL | awk '{print \\$4}'"`
    export OS_AUTH_PUBLIC_URL=`ssh root@${CONTROLLER_HOST} ". openrc; keystone catalog --service identity | grep  publicURL | awk '{print \\$4}'"`
    export OS_EC2_URL=`ssh root@${CONTROLLER_HOST} ". openrc; keystone catalog --service ec2 | grep  internalURL | awk '{print \\$4}'"`

    OS_ADMIN_USERNAME=`ssh root@${CONTROLLER_HOST} ". openrc; echo \\${OS_USERNAME}"`
    OS_ADMIN_PASSWORD=`ssh root@${CONTROLLER_HOST} ". openrc; echo \\${OS_PASSWORD}"`
    OS_ADMIN_TENANT_NAME=`ssh root@${CONTROLLER_HOST} ". openrc; echo \\${OS_TENANT_NAME}"`

    CONTROLLER_OS=`ssh root@${CONTROLLER_HOST} "cat /etc/*-release" | head -n 1 | awk -F"=" '{print $2}'`
    OS_PUBLIC_IP=`echo "${OS_AUTH_PUBLIC_URL}" | grep -Eo "([0-9]{1,3}[\.]){3}[0-9]{1,3}"` || true
    if [ -z "${OS_PUBLIC_IP}" ]
    then
        OS_PUBLIC_NAME=$(echo $OS_AUTH_PUBLIC_URL | awk -F":" '{print $2}' | sed s/"\/"//g)
        OS_PUBLIC_IP=$(ssh root@${CONTROLLER_HOST} "ping -c1 $OS_PUBLIC_NAME" | head -1 | awk '{print $3}' | sed s/"("// | sed s/")"//)
    fi
    if [ -z "${OS_PUBLIC_IP}" ]
    then
        echo "OS_PUBLIC_IP is empty !"
        exit 1
    fi
    if [ ${CONTROLLER_OS} = CentOS ]; then
        OS_DASHBOARD_URL=http://${OS_PUBLIC_IP}/dashboard/
    else
        OS_DASHBOARD_URL=http://${OS_PUBLIC_IP}/horizon/
    fi
    export OS_DASHBOARD_URL

    message "Fuel release is ${FUEL_RELEASE}"
    message "OS_AUTH_URL = ${OS_AUTH_URL}"
    message "OS_DASHBOARD_URL = ${OS_DASHBOARD_URL}"
    message "OS_EC2_URL = ${OS_EC2_URL}"
    message "OS_ADMIN_USERNAME = ${OS_ADMIN_USERNAME}"
    message "OS_ADMIN_PASSWORD = ${OS_ADMIN_PASSWORD}"
    message "OS_ADMIN_TENANT_NAME = ${OS_ADMIN_TENANT_NAME}"

    CONTROLLER="`fuel node | grep controller | wc -l`"
    COMPUTE="`fuel node | grep compute | wc -l`"

    if [ -z "${FUEL_IP}" ]; then
        IP_MASK=`ip a show dev eth1 | grep "inet\b" | awk '{print $2}'`
        FUEL_IP=${IP_MASK%/*}
    fi
    message "Fuel IP is ${FUEL_IP}"
    export FUEL_IP

    # fix permissions on remote logs
    chmod o+r -R /var/log/remote/
    chmod o+r -R /var/log/docker-logs/remote/ || :
}

install_helpers() {
    message "Installing main helpers"
    mkdir -p /var/log/job-reports
    ${VIRTUALENV_DIR}/bin/pip install -U -r ${TOP_DIR}/../../requirements.txt
    ${VIRTUALENV_DIR}/bin/pip install -U psycopg2
}

configure_user() {
    message "Creating and configuring user ${USER_NAME}"

    id -u ${USER_NAME} &>/dev/null || useradd -m ${USER_NAME}
    grep nofile /etc/security/limits.conf || echo '* soft nofile 50000' >> /etc/security/limits.conf ; echo '* hard nofile 50000' >> /etc/security/limits.conf
    cp -r /root/.ssh ${USER_HOME}
    chown -R ${USER_NAME} ${USER_HOME}
    chown -R ${USER_NAME} /var/log/job-reports
    chown -R ${USER_NAME} ${VIRTUALENV_DIR}

    # bashrc
    cat > ${USER_HOME}/.bashrc <<EOF
test "\${PS1}" || return
shopt -s histappend
HISTCONTROL=ignoredups:ignorespace
HISTFILESIZE=2000
HISTSIZE=1000
export EDITOR=vi
alias ..=cd\ ..
alias ls=ls\ --color=auto
alias ll=ls\ --color=auto\ -lhap
alias vi=vim\ -XNn
alias d=df\ -hT
alias f=free\ -m
alias g=grep\ -iI
alias gr=grep\ -riI
alias l=less
alias n=netstat\ -lnptu
alias p=ps\ aux
alias u=du\ -sh
echo \${PATH} | grep ":\${HOME}/bin" >/dev/null || export PATH="\${PATH}:\${HOME}/bin"
if test \$(id -u) -eq 0
then
export PS1='\[\033[01;41m\]\u@\h:\[\033[01;44m\] \W \[\033[01;41m\] #\[\033[0m\] '
else
export PS1='\[\033[01;33m\]\u@\h\[\033[01;0m\]:\[\033[01;34m\]\W\[\033[01;0m\]$ '
fi
cd ${DEST}
. ${VIRTUALENV_DIR}/bin/activate
. ${USER_HOME}/openrc
EOF

    if [ -n "${USE_PROXY}" ]; then
        echo "export HTTP_PROXY=http://${CONTROLLER_HOST}:8888" >> ${USER_HOME}/.bashrc
        echo "export HTTPS_PROXY=http://${CONTROLLER_HOST}:8888" >> ${USER_HOME}/.bashrc
        echo "export OS_INSECURE=1" >> ${USER_HOME}/.bashrc
    fi

    chown ${USER_NAME} ${USER_HOME}/.bashrc

    # vimrc
    cat > ${USER_HOME}/.vimrc <<EOF
set nocompatible
set nobackup
set nowritebackup
set noswapfile
set viminfo=
syntax on
colorscheme slate
set ignorecase
set smartcase
set hlsearch
set smarttab
set expandtab
set tabstop=4
set shiftwidth=4
set softtabstop=4
filetype on
filetype plugin on
EOF
    chown ${USER_NAME} ${USER_HOME}/.vimrc

    cat >> ${USER_HOME}/.ssh/config <<EOF
User root
EOF

    # openrc
    scp ${CONTROLLER_HOST}:/root/openrc /tmp/openrc
    cat /tmp/openrc | sed -e "s/.*LC_ALL.*//" > ${USER_HOME}/openrc
    echo "export FUEL_RELEASE=${FUEL_RELEASE}" >> ${USER_HOME}/openrc
    echo "export OS_AUTH_URL_V3=${OS_AUTH_URL/v2.0/v3}" >> ${USER_HOME}/openrc
    echo "export OS_DASHBOARD_URL=${OS_DASHBOARD_URL}" >> ${USER_HOME}/openrc
    echo "export OS_EC2_URL=${OS_EC2_URL}" >> ${USER_HOME}/openrc
    echo "export CONTROLLER_HOST=${CONTROLLER_HOST}" >> ${USER_HOME}/openrc
    echo "export CONTROLLER=${CONTROLLER}" >> ${USER_HOME}/openrc
    echo "export COMPUTE=${COMPUTE}" >> ${USER_HOME}/openrc
    echo "export OS_ADMIN_USERNAME=${OS_ADMIN_USERNAME}" >> ${USER_HOME}/openrc
    echo "export OS_ADMIN_PASSWORD=${OS_ADMIN_PASSWORD}" >> ${USER_HOME}/openrc
    echo "export OS_ADMIN_TENANT_NAME=${OS_ADMIN_TENANT_NAME}" >> ${USER_HOME}/openrc

    chown -R ${USER_NAME} ${USER_HOME}
    chown -R ${USER_NAME} ${DEST}
}

print_information() {
    echo "======================================================================"
    echo "Information about your installation:"
    echo " * User: ${USER_NAME}"
    echo " * Tempest: ${DEST}/tempest"
    echo " * Rally: ${DEST}/rally"
    echo "======================================================================"
}

main() {
    check_root
    parse_arguments "$@"
    init_variables
    if [ -d ${DEST} ]
    then
      ${TOP_DIR}/clean_tests.sh || :
    fi
    install_system_requirements
    install_python_27
    setup_virtualenv
    init_cluster_variables
    install_helpers
    configure_user
    echo "Tests helpers installed into ${TOP_DIR}/../.."
    message "Deploy all tests"
    cd ${TOP_DIR}
    TEST_FOR_DEPLOY=$(find ./ -mindepth 2 -ipath '*/deploy_*' -iname 'deploy_*.sh')
    for i in ${TEST_FOR_DEPLOY}; do
        message "Start $(basename ${i})"
        ${i}
    done
    print_information
}

main "$@"
${0%/*}/helpers/fuel_getconf.sh || :
