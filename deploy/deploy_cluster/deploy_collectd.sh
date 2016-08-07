#!/bin/bash
set -x


ANSIBLE_PATH="$HOME/.collectd_ansible"
ANSIBLE_INVENTORY="$ANSIBLE_PATH/inventory.py"
ANSIBLE_CMD="ansible-playbook --inventory-file=$ANSIBLE_INVENTORY"


install_tools() {
    if ! command -v pip > /dev/null 2>&1; then
        yum install -y python-pip python-devel
    fi

    if ! command -v git > /dev/null 2>&1; then
        yum install -y git
    fi

    if ! command -v ansible > /dev/null 2>&1; then
        pip install ansible
    fi
}


prepare_ansible() {
    mkdir -p "$ANSIBLE_PATH" || :
    cd "$ANSIBLE_PATH"

    rm -rf fuel_env
    git clone \
        --quiet \
        --single-branch \
        --depth 1 \
        -- \
        https://github.com/martineg/ansible-fuel-inventory.git fuel_env
    cp -f fuel_env/ansible.cfg fuel_env/fuel.ini .
    cp -f fuel_env/fuel.py inventory.py
}


run_ansible() {
    $ANSIBLE_CMD "$ANSIBLE_PATH/playbook/site.yaml"
}


main() {
    install_tools
    prepare_ansible
    run_ansible
}

main
