import ConfigParser
import base64
import json
import urllib2

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

### Parsing env.conf file for required data
parser = ConfigParser.SafeConfigParser()
parser.read('/root/env.conf')
run_id = dict(parser.items('testrail'))['run_id']
fuel_ip = dict(parser.items('fuel'))['fuel_ip']
cluster_id = dict(parser.items('fuel'))['cluster_id']
version = str(dict(parser.items('fuel'))['version'])

repl = int(dict(parser.items('testrail'))['repl'])

def get_tests_ids():
    tests = client.send_get('get_tests/{}'.format(run_id))
    test_names = {}
    for item in tests:
        if "Repl: {}".format(repl) in item['title'] and not "[deprecated]" in item['title']:
            test_names[item['title']] = item['id']
    return test_names

### Define test id's for each case
list_t = get_tests_ids()
for item in list_t.keys():
        if "4 KiB blocks; Read" in item:
                test_4kib_read = list_t[item]
        elif "4 KiB blocks; Write" in item:
                test_4kib_write = list_t[item]
        elif "16MiB blocks; Read" in item:
                test_16mib_read = list_t[item]
        elif "16MiB blocks; Write" in item:
                test_16mib_write = list_t[item]
        elif "latency 10ms" in item:
                test_latency_10_ms = list_t[item]
        elif "latency 30ms" in item:
                test_latency_30_ms = list_t[item]
        elif "latency 100ms" in item:
                test_latency_100_ms = list_t[item]

### Baseline data

base_read_16mib_median = client.send_get('get_test/{}'.format(test_16mib_read))['custom_test_case_steps'][0]['expected']
base_read_16mib_stdev = client.send_get('get_test/{}'.format(test_16mib_read))['custom_test_case_steps'][1]['expected']
base_write_16mib_median = client.send_get('get_test/{}'.format(test_16mib_write))['custom_test_case_steps'][0]['expected']
base_write_16mib_stdev = client.send_get('get_test/{}'.format(test_16mib_write))['custom_test_case_steps'][1]['expected']
base_read_4kib_median = client.send_get('get_test/{}'.format(test_4kib_read))['custom_test_case_steps'][0]['expected']
base_read_4kib_stdev = client.send_get('get_test/{}'.format(test_4kib_read))['custom_test_case_steps'][1]['expected']
base_write_4kib_median = client.send_get('get_test/{}'.format(test_4kib_write))['custom_test_case_steps'][0]['expected']
base_write_4kib_stdev = client.send_get('get_test/{}'.format(test_4kib_write))['custom_test_case_steps'][1]['expected']
base_latency_10_ms = client.send_get('get_test/{}'.format(test_latency_10_ms))['custom_test_case_steps'][0]['expected']
base_latency_30_ms = client.send_get('get_test/{}'.format(test_latency_30_ms))['custom_test_case_steps'][0]['expected']
base_latency_100_ms = client.send_get('get_test/{}'.format(test_latency_100_ms))['custom_test_case_steps'][0]['expected']

read_16mib_median = int(dict(parser.items('testrail'))['read_16mib_median'])
read_16mib_stdev = int(dict(parser.items('testrail'))['read_16mib_stdev'])
write_16mib_median = int(dict(parser.items('testrail'))['write_16mib_median'])
write_16mib_stdev = int(dict(parser.items('testrail'))['write_16mib_stdev'])
read_4kib_median = int(dict(parser.items('testrail'))['read_4kib_median'])
read_4kib_stdev = int(dict(parser.items('testrail'))['read_4kib_stdev'])
write_4kib_median = int(dict(parser.items('testrail'))['write_4kib_median'])
write_4kib_stdev = int(dict(parser.items('testrail'))['write_4kib_stdev'])

latency_10_ms = dict(parser.items('testrail'))['latency_10_ms']
if not latency_10_ms:
    latency_10_ms = 0
latency_30_ms = dict(parser.items('testrail'))['latency_30_ms']
if not latency_30_ms:
    latency_30_ms = 0
latency_100_ms = dict(parser.items('testrail'))['latency_100_ms']

read_16mib_status = 1
read_4kib_status = 1
write_16mib_status = 1
write_4kib_status = 1
latency_10_ms_status = 1
latency_30_ms_status = 1
latency_100_ms_status = 1

### Define status for tests, based on Baseline - 10%
if read_16mib_median < float(base_read_16mib_median)*0.9:
    read_16mib_status = 5
if read_4kib_median < float(base_read_4kib_median)*0.9:
    read_4kib_status = 5
if write_16mib_median < float(base_write_16mib_median)*0.9:
    write_16mib_status = 5
if write_4kib_median < float(base_write_4kib_median)*0.9:
    write_4kib_status = 5
if int(latency_10_ms) < float(base_latency_10_ms)*0.9:
    latency_10_ms_status = 5
if int(latency_30_ms) < float(base_latency_30_ms)*0.9:
    latency_30_ms_status = 5
if int(latency_100_ms) < float(base_latency_100_ms)*0.9:
    latency_100_ms_status = 5
                
for item in list_t.keys():
    print "Name of test: {}, Id: {}".format(item,list_t[item])
### Pushing results to TestRail
client.send_post('add_result/{}'.format(test_4kib_read),
                         {'status_id': read_4kib_status, 'version': str(version), 'custom_throughput': read_4kib_median,
                          'custom_stdev': read_4kib_stdev,
                          'custom_baseline_throughput': base_read_4kib_median,
                          'custom_baseline_stdev': base_read_4kib_stdev})
client.send_post('add_result/{}'.format(test_4kib_write),
                         {'status_id': write_4kib_status, 'version': str(version), 'custom_throughput': int(write_4kib_median),
                          'custom_stdev': int(write_4kib_stdev),
                          'custom_baseline_throughput': int(base_write_4kib_median),
                          'custom_baseline_stdev': int(base_write_4kib_stdev)})
client.send_post('add_result/{}'.format(test_16mib_read),
                         {'status_id': read_16mib_status, 'version': str(version), 'custom_throughput': int(read_16mib_median),
                          'custom_stdev': int(read_16mib_stdev),
                          'custom_baseline_throughput': int(base_read_16mib_median),
                          'custom_baseline_stdev': int(base_read_16mib_stdev)})
client.send_post('add_result/{}'.format(test_16mib_write),
                         {'status_id': write_16mib_status, 'version': str(version), 'custom_throughput': int(write_16mib_median),
                          'custom_stdev': int(write_16mib_stdev),
                          'custom_baseline_throughput': int(base_write_16mib_median),
                          'custom_baseline_stdev': int(base_write_16mib_stdev)})
client.send_post('add_result/{}'.format(test_latency_10_ms),
                         {'status_id': latency_10_ms_status, 'version': str(version), 'custom_throughput': int(latency_10_ms),
                          'custom_baseline_throughput': base_latency_10_ms})
client.send_post('add_result/{}'.format(test_latency_30_ms),
                         {'status_id': latency_30_ms_status, 'version': str(version), 'custom_throughput': int(latency_30_ms),
                          'custom_baseline_throughput': base_latency_30_ms})
client.send_post('add_result/{}'.format(test_latency_100_ms),
                         {'status_id': latency_100_ms_status, 'version': str(version), 'custom_throughput': int(latency_100_ms),
                          'custom_baseline_throughput': base_latency_100_ms})
