#!/bin/bash -xe

general_checks(){
  guestfish --version || { echo "!! FATAL ERROR: libguestfs is not installed" ; exit 1 ; }
  if [ ! -r "/boot/vmlinuz-$(uname -r)" ]; then
    echo "!! FATAL ERROR: can't read /boot/vmlinuz-$(uname -r), this is critical for libguestfs"
    echo "Try to execute 'dpkg-statoverride --update --add root root 0644 /boot/vmlinuz-\$(uname -r)"
    exit 1
  fi
  virsh list || { echo "!! FATAL ERROR: can't work with libvirt" ; exit 1 ; }
  sudo ls / || { echo "!! FATAL ERROR: can't work with sudo" ; exit 1 ; }
  sshpass -V || { echo "!! FATAL ERROR: can't find sshpass" ; exit 1 ; }
}

get_ssh_options() {
 echo "$(get_ssh_options_with_key_auth) -oRSAAuthentication=no -oPubkeyAuthentication=no"
}

get_ssh_options_with_key_auth() {
 echo '-oConnectTimeout=5 -oStrictHostKeyChecking=no '\
 '-oCheckHostIP=no -oUserKnownHostsFile=/dev/null'
}

get_ssh_cmd() {
  echo "sshpass -p ${3} ssh $(get_ssh_options) ${2}@${1}"
}

setup_patch() {
    SSH_CMD=$(get_ssh_cmd $1 $2 $3)
    ${SSH_CMD} "yum -y install patch"
}

setup_zabbix_agent() {
    ZABBIX_RELEASE='http://repo.zabbix.com/zabbix/2.4/rhel/6/x86_64/zabbix-release-2.4-1.el6.noarch.rpm'
    ZABBIX_CONFFILE='/etc/zabbix/zabbix_agentd.conf'
    SSH_CMD=$(get_ssh_cmd $1 $2 $3)
    ${SSH_CMD} "yum -y install ${ZABBIX_RELEASE} && yum -y install zabbix-agent"
    ${SSH_CMD} "test -f ${ZABBIX_CONFFILE} && sed -ri -e 's/^(Server.*=).+$/\1${ZABBIX_SERVER}/' -e 's/^(Hostname=).+$/\1${DOMAIN}/' ${ZABBIX_CONFFILE}"
    ${SSH_CMD} "chkconfig zabbix-agent on; service zabbix-agent start"
}


get_vnc() {
   domain=$1
   ADDR=$(ifconfig main | awk -F ' *|:' '/inet addr/{print $4}')
   VNC_PORT=$(virsh vncdisplay $domain | awk -F ":" '{print $2}' | sed 's/\<[0-9]\>/0&/')
   echo "${ADDR}:59${VNC_PORT}"
}

enable_experimental_features() {
    SSH_CMD=$(get_ssh_cmd $1 root r00tme)
    ${SSH_CMD} 'sed -ie "s/FEATURE_GROUPS:.*$/FEATURE_GROUPS: \[\"experimental\"\]/g" /etc/nailgun/settings.yaml'
    ${SSH_CMD} systemctl restart nailgun
    ${SSH_CMD} systemctl restart nginx
    ${SSH_CMD} cobbler sync
}

is_product_vm_operational() {
   SSH_CMD=$(get_ssh_cmd $1 $2 $3)
   FUEL_DEPLOY_TIMEOUT=3600
   time=0
   LOG_FINISHED=""
   while [ -z "${LOG_FINISHED}" ]; do
       sleep 60
       time=$(($time+60))
       LOG_FINISHED=$(${SSH_CMD} "grep -o 'Fuel node deployment complete' /var/log/puppet/bootstrap_admin_node.log")
       LOG_FAILED=$(${SSH_CMD} "grep 'Fuel node deployment FAILED' /var/log/puppet/bootstrap_admin_node.log")
       if [ -n "${LOG_FAILED}" ]; then
           echo "${LOG_FAILED}"
           exit 1
       fi
       if [ ${time} -ge ${FUEL_DEPLOY_TIMEOUT} ]; then
           echo "Fuel deploy timeout"
           exit 1
       fi
   done
}

wait_for_product_vm_to_install() {
    echo "Waiting for product VM to install. Please do NOT abort the script..."
    # Loop until master node gets successfully installed
    while ! is_product_vm_operational ${1} ${2} ${3} ; do
        sleep 5
    done
}

clean_fuels_on_master_nodes() {
    echo "Clean fuel on the all masternodes"
    SSH_MNODE_OPTIONS=$(get_ssh_options_with_key_auth)
    for MASTER_NODE in $@ ; do
        if [ -n "$(ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh list --all | grep ${DOMAIN})" ]; then
            if [ -z "$(ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh list --all | grep ${DOMAIN} | grep shut)" ]; then
                ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh destroy ${DOMAIN}
            fi
            if [ -n "$(ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh list --all | grep ${DOMAIN} | grep shut)" ]; then
                ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh snapshot-delete ${DOMAIN} ${DOMAIN}-snap || :
                ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh undefine ${DOMAIN}
            fi
        fi
        if [ -n "$(ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh vol-list --pool  ${STORAGE_POOL} | grep ${DOMAIN})" ]; then
            ssh ${SSH_MNODE_OPTIONS} ${MASTER_NODE} sudo virsh vol-delete --pool  ${STORAGE_POOL} ${DOMAIN}.qcow2
        fi
    done
}

create_storage() {
    echo "Creating storage..."
    if [ "fuel-lab-env-${1}" == "fuel-lab-env-10" ]; then
        echo "Was found big env, change image size to 500G"
        FUEL_HDD_SIZE=500
    else
        FUEL_HDD_SIZE=150
    fi
    if [ -n "${4}" ]; then
        FUEL_HDD_SIZE=${4}
    fi
    sudo virsh vol-create-as --name ${2}.qcow2 --capacity ${FUEL_HDD_SIZE}G --format qcow2 --allocation ${FUEL_HDD_SIZE}G --pool ${3}
}

generate_build_name_and_iso_url () {
    if [ -z "${ISO_CUSTOM_URL}" ]; then
        ISO_CUSTOM_URL=${ISO_URL}
    fi
    if [ -n "$ISO_CUSTOM_URL" ]; then
       echo "\$ISO_CUSTOM_URL found, \$ISO_MAIN_URL and \$FUEL_BUILD_NUMBER was ignored"
       if [ -n "$(echo $ISO_CUSTOM_URL | grep torrent)" ]; then
           ISO_CUSTOM_URL=${ISO_CUSTOM_URL%.torrent}
           TORRENT=true
       fi

       ISO_MAIN_URL=$(echo ${ISO_CUSTOM_URL} | cut -d'/' -f1,2,3,4)
       ISO_MAIN_URL="${ISO_MAIN_URL}/"

       if [ -n "$(echo ${ISO_CUSTOM_URL} | grep 'MirantisOpenStack-')" ]; then
           echo "Found release iso"
           FUEL_BUILD_NUMBER=$(echo ${ISO_CUSTOM_URL} | cut -d'/' -f5)
           FUEL_BUILD_NUMBER=${FUEL_BUILD_NUMBER%.iso}
       elif [ -n "$(echo ${ISO_CUSTOM_URL} | grep 'file://')" ] ; then

           if [ "`echo ${ISO_NAME} | grep -E "fuel-[0-9]+\.[0-9]+-"; echo $?`" != "0" ] ; then
               # For downstream (build=9.0-mos-371), custom (build=9.0-custom-176) or community (build=9.0-community-4332) ISOs:
               _BUILD_STRING=`echo ${ISO_CUSTOM_URL} | grep -oE 'fuel-[0-9]+\.[0-9]+-[a-z]+-[0-9]+'`
               if [ -n "$_BUILD_STRING" ] ; then
                   BUILD_STRING=$_BUILD_STRING
               else
                   # For upstream (build=9.0-432) ISOs:
                   _BUILD_STRING=`echo ${ISO_CUSTOM_URL} | grep -oE "fuel-[0-9]+\.[0-9]+-[0-9]+"`
                   if [ -n "$_BUILD_STRING" ] ; then
                       BUILD_STRING=$_BUILD_STRING
                   fi
               fi
           fi

       else
           YEAR=$(date +%Y)
           FUEL_BUILD_NUMBER=$(echo ${ISO_CUSTOM_URL} | grep -oE "fuel-(.*)-${YEAR}")
           FUEL_BUILD_NUMBER=${FUEL_BUILD_NUMBER%-${YEAR}}
           FUEL_BUILD_NUMBER=${FUEL_BUILD_NUMBER#fuel-}
       fi

       if [ -n "$BUILD_STRING" ]; then
           FUEL_BUILD_NUMBER=${BUILD_STRING:5}
           echo "Good news: custom URL build number extracted: ${FUEL_BUILD_NUMBER}"
       else
           FUEL_BUILD_NUMBER="custom"
       fi

    fi


    echo "DEPLOY_AS_RELEASE: ${DEPLOY_AS_RELEASE}"

    if [ -n "${DEPLOY_AS_RELEASE}" -a "${DEPLOY_AS_RELEASE}" != "guess" ]; then
        echo "DEPLOY_AS_RELEASE is set"
        FUEL_BUILD_NUMBER="${DEPLOY_AS_RELEASE}-000"
        echo "Operator selected FUEL_BUILD_NUMBER: ${FUEL_BUILD_NUMBER}"
    fi
}

vm_install() {
    virt-install \
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
      --graphics vnc,listen=0.0.0.0${VNC_PORT} \
      --network ${vm_network_1} \
      --network ${vm_network_2} \
      --network ${vm_network_3}

    sleep 260
}

wait_os_installation() {
    while (true)
    do
       STATUS=$(sudo virsh dominfo ${1} | grep State | awk -F " " '{print $2}')
       if [ ${STATUS} == 'shut' ]
       then
           (
              flock -x -w 120 200 || exit 1
              setup_iso
           ) 200>/tmp/.iso_fuel_setup

           sudo virsh start ${1}
           break
        fi
        sleep 60
    done
    echo "CentOS is installed successfully. Running Fuel master deployment..."
    sleep 700
}

push_pxe_traffic_out() {
    sudo ovs-ofctl add-flow $1 priority=21,dl_src=${2},actions=output:1
}

reconfigure_ssh() {
   SSH_CMD="sshpass -p ${3} ssh ${SSH_OPTIONS} ${2}@${1}"
   while [ -z "$(${SSH_CMD} grep ${FUEL_IP} /etc/ssh/sshd_config)" ]; do
	     echo "Waiting string with ListenAddress ${FUEL_IP}"
       sleep 5
   done
   ${SSH_CMD} sed -i '/ListenAddress/d' /etc/ssh/sshd_config
   ${SSH_CMD} service sshd restart
}

setup_fuel_hdd_image() {
    IMAGE_PATH=$(sudo virsh pool-dumpxml --pool ${STORAGE_POOL} | grep path | tr -d ' ' | sed -e 's/<[^>]*>//g')
    FUEL_RELEASE=${FUEL_BUILD_NUMBER:0:3}

    echo "Setting configs for Fuel ${FUEL_RELEASE}"

    sudo chown root:mos-jenkins ${IMAGE_PATH}/${DOMAIN}.qcow2 || sudo chown root:jenkins ${IMAGE_PATH}/${DOMAIN}.qcow2
    sudo chmod 660 ${IMAGE_PATH}/${DOMAIN}.qcow2

    TMPD=$(mktemp -d)
    echo $FUEL_BUILD_NUMBER > ${TMPD}/FUEL_BUILD_NUMBER

    echo "Creating patch script:"
    PATCH_SCRIPT=$(mktemp)
    echo "#!/bin/bash" > $PATCH_SCRIPT

    case "$FUEL_RELEASE" in
        '7.0')
            turn_off_menu_if_7_0_182_or_less="-rm /root/.showfuelmenu"
            ;;
        '8.0')
            echo "sudo sed -e \"/#Reread/i sed -e \\'s/netmask:.*\\\$/netmask: 255.255.0.0\\/\\' -e \\'s/static_pool_end:.*\\\$/static_pool_end: 10.20.0.255\/\' -e \'s/dhcp_pool_start:.*\$/dhcp_pool_start: 10.20.1.1\/\' -e \'s/dhcp_pool_end:.*\\\$/dhcp_pool_end: 10.20.1.254\/\' -i /etc/fuel/astute.yaml\n\" -i ${TMPD}/bootstrap_admin_node.sh" >> $PATCH_SCRIPT
            get_bootstrap_admin_if_needed="download /usr/local/sbin/bootstrap_admin_node.sh ${TMPD}/bootstrap_admin_node.sh"
            put_bootstrap_admin_if_needed="upload ${TMPD}/bootstrap_admin_node.sh /usr/local/sbin/bootstrap_admin_node.sh"

            echo "sudo sed \"/ListenAddress/s/^/# /g\" -i ${TMPD}/ssh.pp" >> $PATCH_SCRIPT
            get_puppet_ssh_if_needed="glob download /etc/puppet/*/modules/osnailyfacter/manifests/ssh.pp ${TMPD}/ssh.pp"
            put_puppet_ssh_if_needed="glob upload ${TMPD}/ssh.pp /etc/puppet/*/modules/osnailyfacter/manifests/ssh.pp"
            ;;
        '9.0')
            echo "echo \"setsid /finalizer.sh > /dev/null 2>&1 < /dev/null &\" >> ${TMPD}/rc.local" >> $PATCH_SCRIPT
            # create script
            cat > ${TMPD}/finalizer.sh <<FINALIZER
#!/bin/bash

CRITERION="Fuel node deployment complete\!"
FUEL_LOG=/var/log/puppet/bootstrap_admin_node.log
NAP=120
TIMEOUT=3600

function cleanup {
    chmod -x /etc/rc.d/rc.local
    sed -i "/^setsid \/finalizer.sh/d" /etc/rc.d/rc.local
    rm -rf /finalizer.sh
}

cd /

waiting=0
while true; do
    if [ -n "\`grep "\${CRITERION}" \${FUEL_LOG}\`" ]; then
        #
        # take final actions
        #

        # cure firewall
        sed -i "/ListenAddress/s/^/# /g" /etc/ssh/sshd_config
        service sshd restart
        /usr/sbin/iptables -I INPUT -p tcp --dport 22 -j ACCEPT
        /usr/sbin/iptables-save
        sed -i s/"source => \$ssh_network"/"source => \'0.0.0.0\'"/ /etc/puppet/modules/fuel/manifests/iptables.pp
        cleanup
        exit 0
    fi
    sleep \$NAP
    waiting=\$((\$waiting+\$NAP))
    if [ \${waiting} -ge \$TIMEOUT ]; then
        echo "Timeout hit"
        cleanup
        exit 1
    fi
done
FINALIZER
            # updating autostart once of postinstall
            firewall_fix_get="download /etc/rc.d/rc.local ${TMPD}/rc.local"
            firewall_fix_put="upload ${TMPD}/rc.local /etc/rc.d/rc.local"
            firewall_fix_upload="upload ${TMPD}/finalizer.sh /finalizer.sh"
            firewall_fix_add_permission1="chmod 0755 /etc/rc.d/rc.local"
            firewall_fix_add_permission2="chmod 0755 /finalizer.sh"


            ;;
        *)
            ;;
    esac

    echo "sudo sed -e \"s/^NETMASK=.*\$/NETMASK=255.255.0.0/\" -i ${TMPD}/ifcfg-eth0" >> $PATCH_SCRIPT
    echo "sudo sed '/GATEWAY=.*/d' -i ${TMPD}/ifcfg-eth0" >> $PATCH_SCRIPT


    echo "echo \"showmenu=no\" >> ${TMPD}/bootstrap_admin_node.conf" >> $PATCH_SCRIPT
    echo "echo \"export SCALE_LAB_ENV=${VLAN}\" > ${TMPD}/scale_lab.env.sh" >> $PATCH_SCRIPT
    echo "echo \"export SCALE_LAB_UUID=`uuidgen -t`\" >> ${TMPD}/scale_lab.env.sh" >> $PATCH_SCRIPT


    sudo chmod +x $PATCH_SCRIPT
    echo "Patch script created: ${PATCH_SCRIPT}"
    echo "Patch files in folder: ${TMPD}"

    echo "DEVICE=eth1" > ${TMPD}/ifcfg-eth1
    if [ -z "${1}" ]; then
      for i in 'TYPE=Ethernet'  'ONBOOT=yes' 'NM_CONTROLLED=no' 'BOOTPROTO=dhcp' 'PEERDNS=yes'; do
        echo ${i} >> ${TMPD}/ifcfg-eth1
      done
    else
      for i in 'TYPE=Ethernet'  'ONBOOT=yes' 'NM_CONTROLLED=no' 'BOOTPROTO=static' "IPADDR=${1}" "NETMASK=${2}" "GATEWAY=${3}" "DNS1=8.8.8.8" "DNS2=8.8.4.4"; do
        echo ${i} >> ${TMPD}/ifcfg-eth1
      done
    fi
    echo "DEVICE=eth2" > ${TMPD}/ifcfg-eth2
    for i in 'TYPE=Ethernet'  'ONBOOT=yes' 'NM_CONTROLLED=no' 'BOOTPROTO=static' 'PEERDNS=no' 'IPADDR=192.168.0.250' 'NETMASK=255.255.255.0'; do
        echo ${i} >> ${TMPD}/ifcfg-eth2
    done

    echo "Updating Fuel VM image..."

    sudo guestfish <<EOS
add ${IMAGE_PATH}/${DOMAIN}.qcow2
run
list-filesystems
mount /dev/os/root /
download /etc/sysconfig/network-scripts/ifcfg-eth0 ${TMPD}/ifcfg-eth0
download /etc/fuel/bootstrap_admin_node.conf ${TMPD}/bootstrap_admin_node.conf
$get_bootstrap_admin_if_needed
$get_puppet_ssh_if_needed
$firewall_fix_get
! $PATCH_SCRIPT
$turn_off_menu_if_7_0_182_or_less
upload ${TMPD}/ifcfg-eth0 /etc/sysconfig/network-scripts/ifcfg-eth0
upload ${TMPD}/ifcfg-eth1 /etc/sysconfig/network-scripts/ifcfg-eth1
upload ${TMPD}/ifcfg-eth2 /etc/sysconfig/network-scripts/ifcfg-eth2
upload ${TMPD}/bootstrap_admin_node.conf /etc/fuel/bootstrap_admin_node.conf
$put_bootstrap_admin_if_needed
$put_puppet_ssh_if_needed
$firewall_fix_put
$firewall_fix_upload
$firewall_fix_add_permission1
$firewall_fix_add_permission2
upload ${TMPD}/scale_lab.env.sh /etc/profile.d/scale_lab.env.sh
upload ${TMPD}/FUEL_BUILD_NUMBER /root/FUEL_BUILD_NUMBER
EOS

    echo "Updating Fuel VM image... Finished."
}

rebuild_iso() {
    xorriso -version || sudo apt-get -y install xorriso
    ls /usr/lib/syslinux/isohdpfx.bin || sudo apt-get -y install syslinux
    sudo mkdir -p /mnt/iso_fuel_env_${1}
    mkdir -p ${HOME}/iso/env-${1}
    if [ -n "$(mount | grep  /mnt/iso_fuel_env_${1})" ]; then
        sudo umount /mnt/iso_fuel_env_${1}
    fi
    sudo mount -o loop ${2} /mnt/iso_fuel_env_${1}
    sudo rm -rf /tmp/changed_isolinux-config_env_${1}
    mkdir -p /tmp/changed_isolinux-config_env_${1}
    rsync -a /mnt/iso_fuel_env_${1}/ /tmp/changed_isolinux-config_env_${1}/
    sudo umount /mnt/iso_fuel_env_${1}
    sudo sed -i s/"10.20"/"10.2${1}"/g /tmp/changed_isolinux-config_env_${1}/isolinux/isolinux.cfg
    o_iso="${HOME}/iso/env-${1}/$(basename ${2})"
    if [ -f "${o_iso}" ] ; then
        sudo rm -f $o_iso
    fi
    xorriso -as mkisofs \
            -V OpenStack_Fuel -p "Fuel team" \
            -J -R \
            -graft-points \
            -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table \
            -isohybrid-mbr /usr/lib/syslinux/isohdpfx.bin \
            -eltorito-alt-boot -e images/efiboot.img -no-emul-boot \
            -isohybrid-gpt-basdat \
            -o ${o_iso} /tmp/changed_isolinux-config_env_${1}
    rm -rf /tmp/changed_isolinux-config_env_${1}
}
