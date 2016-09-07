import ConfigParser
import base64
import json
import urllib2
import sys

print "aaaaaaa"


parser = ConfigParser.SafeConfigParser()
parser.read('/root/env.conf')
fuel_ip = dict(parser.items('fuel'))['fuel_ip']
interface = dict(parser.items('fuel'))['interface']
create_new_run = dict(parser.items('testrail'))['create_new_run']
suite_id = dict(parser.items('testrail'))['suite_id']
cluster_id = dict(parser.items('fuel'))['cluster_id']
between_nodes = dict(parser.items('testrail'))['between_nodes']
between_nodes = True if between_nodes == "true" else False
version = str(dict(parser.items('fuel'))['version'])
print "create new run: {}".format(create_new_run)
if create_new_run == "true":
    print "suite_id: {}".format(suite_id)
# Testrail API
class APIClient:
    def __init__(self, base_url):
        self.user = ''
        self.password = ''
        if not base_url.endswith('/'):
            base_url += '/'
        self.__url = base_url + 'index.php?/api/v2/'

    def send_get(self, uri):
        return self.__send_request('GET', uri, None)

    def send_post(self, uri, data):
        return self.__send_request('POST', uri, data)

    def __send_request(self, method, uri, data):
        url = self.__url + uri
        request = urllib2.Request(url)
        if (method == 'POST'):
            request.add_data(json.dumps(data))
        auth = base64.b64encode('%s:%s' % (self.user, self.password))
        request.add_header('Authorization', 'Basic %s' % auth)
        request.add_header('Content-Type', 'application/json')

        e = None
        try:
            response = urllib2.urlopen(request).read()
        except urllib2.HTTPError as e:
            response = e.read()

        if response:
            result = json.loads(response)
        else:
            result = {}

        if e != None:
            if result and 'error' in result:
                error = '"' + result['error'] + '"'
            else:
                error = 'No additional error message received'
            raise APIError('TestRail API returned HTTP %s (%s)' %
                           (e.code, error))

        return result


class APIError(Exception):
    pass

client = APIClient('https://mirantis.testrail.com/')
client.user = 'sgudz@mirantis.com'
client.password = 'qwertY123'

def get_run_id():
    create_new_run = dict(parser.items('testrail'))['create_new_run']
    if create_new_run == "true":
        run_name = dict(parser.items('testrail'))['run_name']
        suite_id = int(dict(parser.items('testrail'))['suite_id'])
        data_str = """{"suite_id": %(suite_id)s, "name": "%(name)s", "assignedto_id": 89, "include_all": true}""" %{"suite_id": suite_id, "name": run_name}
        data = json.loads(data_str)
        result = client.send_post('add_run/3', data)
        return result['id']
    else:
        return dict(parser.items('testrail'))['run_id']

def get_tests_ids(run_id):
    tests = client.send_get('get_tests/{}'.format(run_id))
    tests_ids = []
    for item in tests:
        tests_ids.append(item['id'])
    return tests_ids
    
    
def get_token_id(fuel_ip):
    url='http://{}:5000/v2.0/tokens'.format(fuel_ip)
    headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
    post_data = '{"auth": {"tenantName": "admin", "passwordCredentials": {"username": "admin", "password": "admin"}}}'
    req = urllib2.Request(url,data=post_data, headers=headers)
    content = urllib2.urlopen(req)
    json_data = json.load(content)
    return json_data['access']['token']['id']

def get_neutron_conf(fuel_ip, token_id):
    headers = {'X-Auth-Token': token_id}
    url = 'http://{0}:8000/api/clusters/{1}/network_configuration/neutron'.format(fuel_ip,cluster_id)
    req = urllib2.Request(url, headers=headers)
    content = urllib2.urlopen(req)
    json_data = json.load(content)
    return json_data

def get_nodes(fuel_ip, token_id):
    headers = {'X-Auth-Token': token_id}
    url = 'http://{0}:8000/api/nodes/?cluster_id={1}'.format(fuel_ip, cluster_id)
    req = urllib2.Request(url, headers=headers)
    content = urllib2.urlopen(req)
    nodes_data = json.load(content)
    nodes_list = [item['id'] for item in nodes_data]
    return nodes_list

def get_cluster_attributes(fuel_ip, token_id):
    headers = {'X-Auth-Token': token_id}
    url = 'http://{0}:8000/api/clusters/{1}/attributes'.format(fuel_ip, cluster_id)
    req = urllib2.Request(url, headers=headers)
    content = urllib2.urlopen(req)
    attributes_data = json.load(content)
    return attributes_data

def get_computes(fuel_ip, token_id):
    headers = {'X-Auth-Token': token_id}
    compute_ids = []
    for node in get_nodes(fuel_ip, token_id):
        url = 'http://{0}:8000/api/nodes/{1}'.format(fuel_ip, node)
        req = urllib2.Request(url, headers=headers)
        content = urllib2.urlopen(req)
        nodes_data = json.load(content)
        if 'compute' in nodes_data['roles']:
            compute_ids.append(node)
    return compute_ids

# def get_offloading(fuel_ip, token_id):
#     headers = {'X-Auth-Token': token_id}
#     offloading_nodes = {}
#     for node in get_nodes(fuel_ip, token_id):
#         url = 'http://{0}:8000/api/nodes/{1}/interfaces'.format(fuel_ip, node)
#         req = urllib2.Request(url, headers=headers)
#         content = urllib2.urlopen(req)
#         interface_data = json.load(content)
#         for item in interface_data:
#             if item['name'] == interface:
#                 interface_data = item
#         state_list = []
#         for item in interface_data['offloading_modes']:
#             state_list.append(item['state'])
#         for item in state_list:
#             if item is None:
#                 state = "Default"
#             elif not item:
#                 state = False
#             else:
#                 state = True
#             offloading_nodes["Node-" + str(node)] = state
#     return offloading_nodes

if __name__ == "__main__":
    token_id = get_token_id(fuel_ip)
    median = 0
    stdev = 0
    run_id = get_run_id()
    test1, test2, test3, test4, test5, test6, test7, test8 = get_tests_ids(run_id)
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
    # offloading_compute1 = get_offloading(fuel_ip, token_id)['Node-{}'.format(compute_id1)]
    # offloading_compute2 = get_offloading(fuel_ip, token_id)['Node-{}'.format(compute_id2)]
    # if offloading_compute1 and offloading_compute2:
    #     offloading = True
    # elif not offloading_compute1 and not offloading_compute2:
    #     offloading = False
    # else:
    #     offloading = "Unknown"
            
    offloading = True
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
        #print "Wrong cluster config. DVR: {0}, L3HA: {1}, VLAN: {2}, VXLAN: {3}, BETWEEN_NODES: {4}, OFFLOADING: {5}".format(dvr, l3ha, vlan, vxlan, between_nodes, offloading)
        #raise ClusterError("DVR: {0}, L3HA: {1}, VLAN: {2}, VXLAN: {3}, BETWEEN_NODES: {4}, OFFLOADING: {5}".format(dvr, l3ha, vlan, vxlan, between_nodes, offloading))
        #sys.exit("Wrong cluster config")
        test_id = test8
    
    base_median = client.send_get('get_test/{}'.format(test_id))['custom_test_case_steps'][0]['expected']
    base_stdev = client.send_get('get_test/{}'.format(test_id))['custom_test_case_steps'][1]['expected']
    
    
    
    print "Test ID for testing: {}".format(test_id)
    print "DVR: {0}, L3HA: {1}, VLAN: {2}, VXLAN: {3}, BETWEEN_NODES: {4}, OFFLOADING: {5}".format(dvr, l3ha, vlan, vxlan, between_nodes, offloading)
    content = dict(parser.items('test_json'))['json_data']
    json_data = json.loads(content)
    item = [each for each in json_data['records']]
    for i in range(len(item)):
        try:
            median = int(round(json_data['records'][item[i]]['stats']['bandwidth']['median'], 0))
            stdev = int(round(json_data['records'][item[i]]['stats']['bandwidth']['stdev'], 0))
        except KeyError:
            continue
    
    test_glob_status = test_custom_median_status = test_custom_stdev_status = 1
    if median < float(base_median) * 0.9:
        test_glob_status = test_custom_median_status = 5
    if stdev < float(base_stdev) * 0.5:
        test_custom_stdev_status = 5
    
    ### Collecting results
    custom_test_res = [{'status_id': test_custom_median_status, 'content': 'Check [network bandwidth, Median; Mbps]',
                             'expected': str(base_median), 'actual': str(median)},
                            {'status_id': test_custom_stdev_status, 'content': 'Check [deviation; pcs]', 'expected': str(base_stdev),
                             'actual': str(stdev)}]
    glob_test_result = {'test_id': test_id, 'status_id': test_glob_status, 'version': str(version),
                     'custom_test_case_steps_results': custom_test_res}
    
    results_all_dict = {'results': [glob_test_result]}
    client.send_post('add_results/{}'.format(run_id), results_all_dict)
