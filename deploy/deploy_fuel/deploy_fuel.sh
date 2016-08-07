#!/bin/bash -xe
WDIR=$(cd `dirname "${BASH_SOURCE[0]}"` && pwd)
cd "${WDIR}"
source ./deploy_fuel_lib.sh


USER=${USER:-neutron-lab}
IPMI_USER=${IPMI_USER:-engineer}
IPMI_PASSWORD=${IPMI_PASSWORD:-Fa#iR36cHE0}
ISO_MAIN_URL=${ISO_MAIN_URL:-http://mc0n1-msk.msk.mirantis.net/fuelweb-iso/}
ISO_CUSTOM_URL=${ISO_CUSTOM_URL}
VLAN=${VLAN:-10}
ISO_PATH=${ISO_PATH}
STORAGE_POOL=${STORAGE_POOL:-default}
DOWNLOAD_ISO_DIR=${DOWNLOAD_ISO_DIR:-~/iso/}
TORRENT=false
DOMAIN=${DOMAIN:-fuel-lab-env-${VLAN}}
FROM_SNAPSHOT=${FROM_SNAPSHOT:-false}

ZABBIX_SERVER=172.18.160.61
MASTER_NODES="172.16.44.5 172.16.44.7 172.16.44.8"



main() {
    general_checks

    if ${FROM_SNAPSHOT}; then
       virsh snapshot-revert ${DOMAIN} ${DOMAIN}-snap
       exit 0
    fi
    generate_build_name_and_iso_url

    echo "FUEL_BUILD_NUMBER is ${FUEL_BUILD_NUMBER}"
    echo "ISO_CUSTOM_URL is ${ISO_CUSTOM_URL}"

    DISK=/var/lib/libvirt/images/${DOMAIN}.qcow2

    mkdir -p ${DOWNLOAD_ISO_DIR}

    FUEL_DEV_NET='172.18.161.0/24'
    FUEL_DEV_GW='172.18.161.1'

    #Default for 100 nodes lab
    vm_master_ip=172.16.44.${VLAN}
    vm_master_ram=16384
    vm_master_cpu=6
    vm_network_1="network=10g-1,model=virtio"
    vm_network_2="network=1g-1,model=virtio,mac=52:54:00:ba:6e:${VLAN}"
    vm_network_3="network=10g-1,model=virtio"
    vm_master_username=root
    vm_master_password=r00tme
    cluster_nodes=20
    vm_master_pxe_net="10.20.0.0/16"
    VNC_PORT=",port=59${VLAN}"

    gateway_ip=172.16.44.1


    if [ -n "$(echo ${ISO_CUSTOM_URL} | grep 'file://')" ] ; then
        ISO=${ISO_CUSTOM_URL#file://}
    else
        initial_checks
        ISO=${DOWNLOAD_ISO_DIR}/${ISO_FUEL}
        download_iso
    fi
    clean_fuels_on_master_nodes ${MASTER_NODES}
    create_storage ${VLAN} ${DOMAIN} ${STORAGE_POOL}
    vm_install
    wait_os_installation ${DOMAIN}
    # Wait until the machine gets installed and Puppet completes its run
    wait_for_product_vm_to_install ${vm_master_ip} ${vm_master_username} ${vm_master_password}
    # Since workaround scripts can be executed at any moment install patch package just
    # after Fuel master node is deployed
    setup_patch ${vm_master_ip} ${vm_master_username} ${vm_master_password}
    # Install and configure zabbix agent. Don't fail task on failure.
    setup_zabbix_agent ${vm_master_ip} ${vm_master_username} ${vm_master_password} || :
    virsh snapshot-delete ${DOMAIN}-snap || :
    virsh snapshot-create-as ${DOMAIN} ${DOMAIN}-snap
}

initial_checks() {
    if [ -z "${FUEL_BUILD_NUMBER}" ]; then
        echo "Env \$FUEL_BUILD_NUMBER must be set"
        exit 1
    fi
    if [  -z "${VLAN}" ]; then
        echo "Env \$VLAN myst be set "
        exit 1
    fi
    set +e
    if [ -n "$(echo $ISO_CUSTOM_URL | grep 'MirantisOpenStack-')" ]; then
        ISO_FUEL=$(curl -s ${ISO_MAIN_URL} | grep 'iso</a>' | grep -oE '>(.*)</a>' | grep -oE "${FUEL_BUILD_NUMBER}.iso")
    else
        ISO_FUEL=$(curl -s ${ISO_MAIN_URL} | grep 'iso</a>' | grep -oE '>(.*)</a>' | grep -oE 'f.*.iso' | grep "fuel-${FUEL_BUILD_NUMBER}-20")
    fi
    if [ -z "${ISO_FUEL}" ]; then
        echo "Can'f find ISO $ISO_FUEL for build ${FUEL_BUILD_NUMBER} in the ${ISO_MAIN_URL}"
        exit 1
    fi
    set -e
}


download_iso() {
    cd ${DOWNLOAD_ISO_DIR}
    flock -w 14400 /tmp/.iso_fuel_download  wget -nc --tries 10 ${ISO_MAIN_URL}/${ISO_FUEL}.md5
    if  ${TORRENT} ; then
        flock -w 14400 /tmp/.iso_fuel_download aria2c --follow-torrent=mem --check-integrity --seed-time=0 ${ISO_MAIN_URL}/${ISO_FUEL}.torrent
    else
        flock -w 14400 /tmp/.iso_fuel_download wget --progress=dot:giga -c --tries 10  ${ISO_MAIN_URL}/${ISO_FUEL}
    fi
    if ! md5sum --check --quiet ${ISO_FUEL}.md5; then
        echo "Bad MD5 for ${MD5_FUEL_ISO_LOCAL}"
        rm -rf ./${ISO_FUEL}
        exit 1
    fi
    sudo chmod a+rw ${ISO_FUEL}
    cd -
}

setup_iso() {
    setup_fuel_hdd_image
    virsh dumpxml ${DOMAIN} > /tmp/${DOMAIN}.xml
    sed "0,/network='10g-1'\\/>/s//network='10g-1' portgroup='vlan-${VLAN}'\\/>/" -i /tmp/${DOMAIN}.xml
    sed "0,/network='10g-1'\\/>/s//network='10g-1' portgroup='vlan-${VLAN}0'\\/>/" -i /tmp/${DOMAIN}.xml
    sed -e 's/writeback/unsafe/g' -i /tmp/${DOMAIN}.xml
    virsh define /tmp/${DOMAIN}.xml
    rm -f /tmp/${DOMAIN}.xml
}



main "$@"
