#!/bin/bash -e

echo "Install OVS"
mkdir -p ~/rpmbuild/SOURCES
cd ~/rpmbuild/SOURCES/
wget http://openvswitch.org/releases/openvswitch-2.5.0.tar.gz
tar xfz openvswitch-2.5.0.tar.gz
sudo yum -y install wget openssl-devel gcc make python-devel openssl-devel \
kernel-devel graphviz kernel-debug-devel autoconf automake rpm-build \
redhat-rpm-config libtool python-twisted-core python-zope-interface \
PyQt4 desktop-file-utils libcap-ng-devel groff checkpolicy \
selinux-policy-devel
rpmbuild -bb --nocheck openvswitch-2.5.0/rhel/openvswitch-fedora.spec
sudo yum -y localinstall ../RPMS/x86_64/openvswitch-2.5.0-1.el7.centos.x86_64.rpm
sudo systemctl start openvswitch.service
sudo systemctl enable openvswitch

echo "Create vswitch"
sudo ovs-vsctl add-br vswitch00
sudo ovs-vsctl add-port vswitch00 bond0
sudo ovs-vsctl set port vswitch00 tag=130

echo "Deploy libvirt"
sudo yum install -y libvirt qemu-kvm

echo "Configure libvirt"
sudo virsh pool-define default_pool.xml
sudo virsh pool-autostart default
sudo virsh pool-start default
sudo virsh net-define vswitch00-net.xml
sudo virsh net-start vswitch00
sudo virsh net-autostart vswitch00
sudo virsh net-destroy default
sudo virsh net-undefine default

echo "Reconfigure default network"
tar czvf ~/network-scripts.tar.gz /etc/sysconfig/network-scripts
sudo cp ifcfg-vswitch00 /etc/sysconfig/network-scripts/
sudo rm -f /etc/sysconfig/network-scripts/ifcfg-bond0.130
sudo sed -i -e 's/BOOTPROTO=dhcp/BOOTPROTO=none/' /etc/sysconfig/network-scripts/ifcfg-bond0
sudo sed -i -e '/PEERDNS=yes/d'  /etc/sysconfig/network-scripts/ifcfg-bond0
sudo sed -i -e '/PEERROUTES=yes/d' /etc/sysconfig/network-scripts/ifcfg-bond0
sudo sed -i -e '/DEFROUTE=yes/d' /etc/sysconfig/network-scripts/ifcfg-bond0
