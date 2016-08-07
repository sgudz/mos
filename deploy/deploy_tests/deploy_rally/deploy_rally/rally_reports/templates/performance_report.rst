
.. _Measuring_performance_of_openstack_services:

*********************************************************
Results of measuring performance of Openstack Services
*********************************************************

:Abstract:

  This document includes performance test results of `OpenStack`_
  service. All test have been performed
  regarding :ref:`Measuring_performance_of_openstack_services`


Environment description
=======================
Environment contains 5 types of servers:

- rally node
- controller node
- compute-osd node
- compute node
- osd node

.. table:: Amount of servers each role

   +------------+--------------+
   |Role        |Servers count |
   +============+==============+
   |rally       |1             |
   +------------+--------------+
   |controller  |{{results.roles.controller.count}}{{ ' ' * (14 - results.roles.controller.count|string|length) }}|
   +------------+--------------+
   |compute     |{{results.roles.compute.count}}{{ ' ' * (14 - results.roles.compute.count|string|length) }}|
   +------------+--------------+
   |compute-osd |{{results.roles.compute_osd.count}}{{ ' ' * (14 - results.roles.compute_osd.count|string|length) }}|
   +------------+--------------+
   |osd         |{{results.roles.osd.count}}{{ ' ' * (14 - results.roles.osd.count|string|length) }}|
   +------------+--------------+

Hardware configuration of each server
-------------------------------------
All servers have same configuration describing in table below

.. table:: Description of servers hardware

   +-------+----------------+-------------------------------+
   |server |vendor,model    |HP,DL380 Gen9                  |
   +-------+----------------+-------------------------------+
   |CPU    |vendor,model    |Intel,E5-2680 v3               |
   |       +----------------+-------------------------------+
   |       |processor_count |2                              |
   |       +----------------+-------------------------------+
   |       |core_count      |12                             |
   |       +----------------+-------------------------------+
   |       |frequency_MHz   |2500                           |
   +-------+----------------+-------------------------------+
   |RAM    |vendor,model    |HP,752369-081                  |
   |       +----------------+-------------------------------+
   |       |amount_MB       |262144                         |
   +-------+----------------+-------------------------------+
   |NETWORK|interface_name  |p1p1                           |
   |       +----------------+-------------------------------+
   |       |vendor,model    |Intel,X710 Dual Port           |
   |       +----------------+-------------------------------+
   |       |bandwidth       |10G                            |
   +-------+----------------+-------------------------------+
   |STORAGE|dev_name        |/dev/sda                       |
   |       +----------------+-------------------------------+
   |       |vendor,model    | | raid10 - HP P840            |
   |       |                | | 12 disks EH0600JEDHE        |
   |       +----------------+-------------------------------+
   |       |SSD/HDD         |HDD                            |
   |       +----------------+-------------------------------+
   |       |size            | 3,6TB                         |
   +-------+----------------+-------------------------------+

Network configuration of each server
---------------------------------------------------------------------
Each server have same network configuration:

.. image:: Network_Scheme.png
   :alt: Network Scheme of the environment

Here is the part of switch configuration for each switch port which connected to
ens1f0 interface of a server:

.. code:: bash

   switchport mode trunk
   switchport trunk native vlan 600
   switchport trunk allowed vlan 600-602,630-649
   spanning-tree port type edge trunk
   spanning-tree bpduguard enable
   no snmp trap link-status

Software configuration on servers with controller, compute and compute-osd roles
--------------------------------------------------------------------------------
.. table:: Services on servers by role

   +------------+--------------------------+
   |Role        |Service name              |
   +============+==========================+
   |controller  |horizon                   |
   |            |keystone                  |
   |            |nova-api                  |
   |            |nava-scheduler            |
   |            |nova-cert                 |
   |            |nova-conductor            |
   |            |nova-consoleauth          |
   |            |nova-consoleproxy         |
   |            |cinder-api                |
   |            |cinder-backup             |
   |            |cinder-scheduler          |
   |            |cinder-volume             |
   |            |glance-api                |
   |            |glance-glare              |
   |            |glance-registry           |
   |            |neutron-dhcp-agent        |
   |            |neutron-l3-agent          |
   |            |neutron-metadata-agent    |
   |            |neutron-openvswitch-agent |
   |            |neutron-server            |
   |            |heat-api                  |
   |            |heat-api-cfn              |
   |            |heat-api-cloudwatch       |
   |            |ceph-mon                  |
   |            |rados-gw                  |
   |            |heat-engine               |
   +------------+--------------------------+
   |compute     |nova-compute              |
   |            |neutron-l3-agent          |
   |            |neutron-metadata-agent    |
   |            |neutron-openvswitch-agent |
   +------------+--------------------------+
   |compute-osd |nova-compute              |
   |            |neutron-l3-agent          |
   |            |neutron-metadata-agent    |
   |            |neutron-openvswitch-agent |
   |            |ceph-osd                  |
   +------------+--------------------------+
   |osd         |ceph-osd                  |
   +------------+--------------------------+

.. table:: Software version on servers with controller, compute and compute-osd roles

   +------------+-------------------+
   |Software    |Version            |
   +============+===================+
   |OpenStack   |Mitaka             |
   +------------+-------------------+
   |Ceph        |Hammer             |
   +------------+-------------------+
   |Ubuntu      |Ubuntu 14.04.3 LTS |
   +------------+-------------------+

You can find outputs of some commands and /etc folder in the following archives:
{% for index in range(1,results.roles.controller.count+1) %}
:download:`controller-{{index}}.tar.gz <controller-{{index}}.tar.gz>`
{% endfor %}
{% if results.roles.compute.count > 0 %}
:download:`compute-1.tar.gz <compute-1.tar.gz>`
{% endif %}
{% if results.roles.compute_osd.count > 0 %}
:download:`compute-osd-1.tar.gz <compute-osd-1.tar.gz>`
{% endif %}
{% if results.roles.osd.count > 0 %}
:download:`osd-1.tar.gz <osd-1.tar.gz>`
{% endif %}

Software configuration on servers with rally role
-------------------------------------------------
On this server should be installed Rally. How to do it you can find in `Rally installation documentation`_

.. table:: Software version on server with rally role

   +------------+-------------------+
   |Software    |Version            |
   +============+===================+
   |Rally       |0.4.0              |
   +------------+-------------------+
   |Ubuntu      |Ubuntu 14.04.3 LTS |
   +------------+-------------------+

Testing process
===============
1. Create workdirectory on server. In future we will call they WORK_DIR
2. Create directory "plugins" in WORK_DIR and copy to they :download:`nova_scale.py <./nova_scale.py>` plugin.
3. Create directory "scenarios" in WORK_DIR and copy to it
   :download:`boot_attach_live_migrate_and_delete_server_with_secgroups.json <./boot_attach_live_migrate_and_delete_server_with_secgroups.json>`,
   :download:`create-and-delete-image.json <./create-and-delete-image.json>` and :download:`keystone.json <./keystone.json>` scenarios.
4. Create deployment.json file in WORK_DIR and fill it with OpenStack environment info.
   It should looks like this:

   .. code:: json

      {
        "admin": {
          "password": "password",
          "tenant_name": "tenant",
          "username": "user"
        },
        "auth_url": "http://1.2.3.4:5000/v2.0",
        "region_name": "RegionOne",
        "type": "ExistingCloud",
        "endpoint_type": "internal",
        "admin_port": 35357,
        "https_insecure": true
      }

5. Create job-params.yaml file in WORK_DIR and fill it with scenarios info.
   It should looks like this:

   .. code:: yaml

      ---
          concurrency: 5
          compute: 3
          start_cidr: "1.0.0.0/16"
          current_path: "/home/rally/rally-scenarios/heat/"
          floating_ip_amount: 800
          floating_net: "admin_floating_net"
          vlan_amount: 1025
          gre_enabled: false
          http_server_with_glance_images: "1.2.3.4"

6. Perform tests:

   .. code:: bash

      ${WORK_DIR:?}
      DEPLOYMENT_NAME="$(uuidgen)"
      DEPLOYMENT_CONFIG="${WORK_DIR}/deployment.json"
      PLUGIN_PATH="${WORK_DIR}/plugins/nova_scale.py"
      JOB_PARAMS_CONFIG="${WORK_DIR}/job-params.yaml"
      rally deployment create --filename $(DEPLOYMENT_CONFIG) --name $(DEPLOYMENT_NAME)
      SCENARIOS="boot_attach_live_migrate_and_delete_server_with_secgroups create-and-delete-image keystone.json"
      for scenario in SCENARIOS; do
        rally --plugin-paths ${PLUGINS_PATH} task start --tag ${scenario} --task-args-file ${JOB_PARAMS_CONFIG} ${WORK_DR}/scenarios/${scenario}
      done
      task_list="$(rally task list --uuids-only)"
      rally task report --tasks ${task_list} --out=${WORK_DIR}/rally_report.html

As a result of this part we got the following HTML file:

:download:`rally_report.html <./rally_report.html>`

Test results
============
{% for item in results.data|dictsort %}
{{item[0]}}
{{ "-" * item[0]|length}}
{{ item[1].table }}
{% endfor %}

.. references:

.. _Rally installation documentation: https://rally.readthedocs.io/en/latest/install.html
