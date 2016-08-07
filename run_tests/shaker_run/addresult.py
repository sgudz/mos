from fuelapi import *

median = 0
stdev = 0
test1, test2, test3, test4, test5, test6, test7, test8 = get_tests_ids()
seg_type = get_neutron_conf(fuel_ip, token_id)['networking_parameters']['segmentation_type']
if seg_type == 'vlan':
    vlan = True
    vxlan = False
else:
    vlan = False
    vxlan = True
dvr = get_cluster_attributes(fuel_ip, token_id)['editable']['neutron_advanced_configuration']['neutron_dvr']['value']
l3ha = get_cluster_attributes(fuel_ip, token_id)['editable']['neutron_advanced_configuration']['neutron_l3_ha']['value']
nodes = get_nodes(fuel_ip, token_id)
compute_id1 = get_computes(fuel_ip, token_id)[0]
compute_id2 = get_computes(fuel_ip, token_id)[1]
offloading_compute1 = get_offloading(fuel_ip, token_id)['Node-{}'.format(compute_id1)]
offloading_compute2 = get_offloading(fuel_ip, token_id)['Node-{}'.format(compute_id2)]
if offloading_compute1 and offloading_compute2:
    offloading = True
elif not offloading_compute1 and not offloading_compute2:
    offloading = False
else:
    offloading = "Unknown"
if dvr and vxlan and offloading:
    test_id = test3
elif dvr and vlan and offloading:
    test_id = test4
elif dvr and vxlan:
    test_id = test1
elif dvr and vlan:
    test_id = test2
elif l3ha and vxlan and offloading and between_nodes:
    test_id = test5
elif l3ha and vxlan and offloading:
    test_id = test6
elif l3ha and vlan and offloading and between_nodes:
    test_id = test7
elif l3ha and vlan and offloading:
    test_id = test8
else:
    print "wrong test"
print "Test ID for testing: {}".format(test_id)
print "DVR: {0}, L3HA: {1}, VLAN: {2}, VXLAN: {3}, BETWEEN_NODES: {4}, OFFLOADING: {5}".format(dvr, l3ha, vlan, vxlan, between_nodes, offloading)
content = dict(parser.items('test_json'))['json_data']
json_data = json.loads(content)
item = [each for each in json_data['records']]
for i in range(len(item)):
    try:
        median = json_data['records'][item[i]]['stats']['bandwidth']['median']
        stdev = json_data['records'][item[i]]['stats']['bandwidth']['stdev']
    except KeyError:
        continue

client.send_post('add_result/{}'.format(test_id),
                          {'status_id': 1, 'version': str(version), 'custom_throughput': int(median),
                           'custom_stdev': int(stdev)})
