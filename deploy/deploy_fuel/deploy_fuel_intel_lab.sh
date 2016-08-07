#!/bin/bash -xe
WDIR=$(cd `dirname "${BASH_SOURCE[0]}"` && pwd)
cd "${WDIR}"
source ./deploy_fuel_lib.sh

ISO_URL=${ISO_URL}
ISO_PATH=${ISO_PATH}
STORAGE_POOL=${STORAGE_POOL:-default}
DOWNLOAD_ISO_DIR=${DOWNLOAD_ISO_DIR:-~/iso/}
DOMAIN=${DOMAIN:-fuel-env-$ENV}
ISO_LOCAL=false

FUEL_IP="10.20.0.2"
LAST_IP=$((60+${ENV}))
FUEL_IP_FOR_ACCESS="10.3.60.${LAST_IP}"
FUEL_MASK_FOR_ACCESS="255.255.248.0"
FUEL_GW_FOR_ACCESS="10.3.56.1"
LAST_MAC_PXE=$(echo 16o$((0x1e + ${ENV}))p | dc)
FUEL_MAC_PXE="52:54:bb:73:62:${LAST_MAC_PXE}"
LAST_MAX_PUBLIC=$(echo 16o$((0x60 + ${ENV}))p | dc)
FUEL_MAC_PUBLIC="52:54:bb:ba:6e:${LAST_MAX_PUBLIC}"
OVSWITCH_PXE="vswitch00"
OVSWITCH_PUBLIC="vswitch00"
MASTER_NODES="10.3.57.28"
PXE_VLAN=131
PUBLIC_VLAN=130

VNC_PORT=$((5959+${ENV}))

ISO_FUEL=$(echo ${ISO_URL} | grep -oE "/fuel-.*iso" | tr -d '/' )

SSH_OPTIONS=$(get_ssh_options)


main() {
    general_checks

    if ${FROM_SNAPSHOT}; then
       sudo virsh snapshot-revert ${DOMAIN} ${DOMAIN}-snap
       exit 0
    fi
    check_iso_url
    generate_build_name_and_iso_url
    echo "FUEL_BUILD_NUMBER is ${FUEL_BUILD_NUMBER}"
    echo "ISO_URL is ${ISO_URL}"

    DISK=/var/lib/libvirt/images/${DOMAIN}.qcow2

    mkdir -p ${DOWNLOAD_ISO_DIR}

    vm_master_ip=${vm_master_ip:-172.20.8.222}
    vm_master_ram=${vm_master_ram:-32000}
    vm_master_cpu=${vm_master_cpu:-12}
    vm_network_1="network=${OVSWITCH_PXE},model=virtio,mac=${FUEL_MAC_PXE}"
    vm_network_2="network=${OVSWITCH_PUBLIC},model=virtio,mac=${FUEL_MAC_PUBLIC}"
    vm_master_username=root
    vm_master_password=r00tme
    vm_master_pxe_net="10.20.0.0/16"
    gateway_ip="10.3.56.1"
    if [ -n "$(echo ${ISO_URL} | grep 'file://')" ] ; then
        ISO=${ISO_URL#file://}
    else
        initial_checks
        ISO=${DOWNLOAD_ISO_DIR}/${ISO_FUEL}
        download_iso
    fi

    rebuild_iso ${ENV} ${ISO}
    ISO="${HOME}/iso/env-${ENV}/${ISO_FUEL}"
    clean_fuels_on_master_nodes ${MASTER_NODES}
    create_storage ${ENV} ${DOMAIN} ${STORAGE_POOL} 500
    sudo virt-install \
      --name=${DOMAIN} \
      --cpu host \
      --ram=${vm_master_ram} \
      --cdrom "${ISO}" \
      --disk "vol=${STORAGE_POOL}/${DOMAIN}.qcow2,cache=writeback" \
      --vcpus=${vm_master_cpu} \
      --os-type=linux \
      --os-variant=rhel6 \
      --virt-type=kvm \
      --boot=cdrom,hd \
      --noautoconsole \
      --graphics vnc,listen=0.0.0.0,port=${VNC_PORT} \
      --network ${vm_network_1} \
      --network ${vm_network_2}

    sleep 160
    wait_os_installation ${DOMAIN}
    # Wait until the machine gets installed and Puppet completes its run
    push_pxe_traffic_out ${OVSWITCH_PXE} ${FUEL_MAC_PXE}
    # Wait until the machine gets installed and Puppet completes its run
    wait_for_product_vm_to_install $FUEL_IP_FOR_ACCESS $vm_master_username $vm_master_password
    sudo virsh snapshot-delete ${DOMAIN}-snap || :
    sudo virsh snapshot-create-as ${DOMAIN} ${DOMAIN}-snap
}

initial_checks() {
    if [ -z "${FUEL_BUILD_NUMBER}" ]; then
        echo "Env \$FUEL_BUILD_NUMBER must be set"
        exit 1
    fi
}

check_iso_url () {
    if  [ -n "$(echo ${ISO_URL} | grep 'file://')" ]; then
        ISO_LOCAL=true
    fi
}

download_iso() {
    cd ${DOWNLOAD_ISO_DIR}
    if ! $ISO_LOCAL ; then
        flock -w 14400 /tmp/.iso_fuel_download aria2c -c --follow-torrent=mem --check-integrity --seed-time=0 $ISO_URL
    fi
    sudo chmod a+rw ${ISO_FUEL}
    cd -
}

setup_iso() {
    setup_fuel_hdd_image ${FUEL_IP_FOR_ACCESS} ${FUEL_MASK_FOR_ACCESS} ${gateway_ip}
    sudo virsh dumpxml ${DOMAIN} > /tmp/${DOMAIN}.xml
    sudo sed "0,/network='${OVSWITCH_PXE}'\\/>/s//network='${OVSWITCH_PXE}' portgroup='vlan-${PXE_VLAN}'\\/>/" -i /tmp/${DOMAIN}.xml
    sudo sed "0,/network='${OVSWITCH_PUBLIC}'\\/>/s//network='${OVSWITCH_PUBLIC}' portgroup='vlan-${PUBLIC_VLAN}'\\/>/" -i /tmp/${DOMAIN}.xml
    sudo sed "0,/network='${OVSWITCH_PXE}' portgroup='vlan-${PXE_VLAN}'\\/>/s//network='${OVSWITCH_PXE}'\\/>/" -i /tmp/${DOMAIN}.xml
    sudo sed -e 's/writeback/unsafe/g' -i /tmp/${DOMAIN}.xml
    sudo virsh define /tmp/${DOMAIN}.xml
    rm -f /tmp/${DOMAIN}.xml
}


main "$@"
