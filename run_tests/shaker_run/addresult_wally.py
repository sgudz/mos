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

def get_tests_ids():
    tests = client.send_get('get_tests/{}'.format(run_id))
    tests_ids = []
    test_names = {}
    for item in tests:
        tests_ids.append(item['id'])
        test_names[item['title']] = item['id']
    return test_names

parser = ConfigParser.SafeConfigParser()
parser.read('/root/env.conf')
run_id = dict(parser.items('testrail'))['run_id']
fuel_ip = dict(parser.items('fuel'))['fuel_ip']
cluster_id = dict(parser.items('fuel'))['cluster_id']
version = str(dict(parser.items('fuel'))['version'])
read_16mib_median = dict(parser.items('testrail'))['read_16mib_median']
read_16mib_stdev = dict(parser.items('testrail'))['read_16mib_stdev']
write_16mib_median = dict(parser.items('testrail'))['write_16mib_median']
write_16mib_stdev = dict(parser.items('testrail'))['write_16mib_stdev']
read_4kib_median = dict(parser.items('testrail'))['read_4kib_median']
read_4kib_stdev = dict(parser.items('testrail'))['read_4kib_stdev']
write_4kib_median = dict(parser.items('testrail'))['write_4kib_median']
write_4kib_stdev = dict(parser.items('testrail'))['write_4kib_stdev']
latency_10iops = dict(parser.items('testrail'))['latency_10iops']
latency_30iops = dict(parser.items('testrail'))['latency_30iops']
latency_100iops = dict(parser.items('testrail'))['latency_100iops']
base_read_16mib_median = dict(parser.items('testrail'))['base_read_16mib_median']
base_read_16mib_stdev = dict(parser.items('testrail'))['base_read_16mib_stdev']
base_write_16mib_median = dict(parser.items('testrail'))['base_write_16mib_median']
base_write_16mib_stdev = dict(parser.items('testrail'))['base_write_16mib_stdev']
base_read_4kib_median = dict(parser.items('testrail'))['base_read_4kib_median']
base_read_4kib_stdev = dict(parser.items('testrail'))['base_read_4kib_stdev']
base_write_4kib_median = dict(parser.items('testrail'))['base_write_4kib_median']
base_write_4kib_stdev = dict(parser.items('testrail'))['base_write_4kib_stdev']
base_latency_10iops = dict(parser.items('testrail'))['base_latency_10iops']
base_latency_30iops = dict(parser.items('testrail'))['base_latency_30iops']
base_latency_100iops = dict(parser.items('testrail'))['base_latency_100iops']

status = 1
comment = "passed"

if (float(read_16mib_median) < float(base_read_16mib_median) - float(base_read_16mib_median) * 0.1) or (float(read_16mib_stdev) < (float(base_read_16mib_stdev) - float(base_read_16mib_stdev) * 0.1)):
    status = 5
    comment = "Value less then Baseline value more then 10 %"
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
                test_latency_10ms = list_t[item]
        elif "latency 30ms" in item:
                test_latency_30ms = list_t[item]
        elif "latency 100ms" in item:
                test_latency_100ms = list_t[item]
client.send_post('add_result/{}'.format(test_4kib_read),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(read_4kib_median),
                          'custom_stdev': int(read_4kib_stdev),
                          'custom_baseline_throughput': int(base_read_4kib_median),
                          'custom_baseline_stdev': int(base_read_4kib_stdev)})
client.send_post('add_result/{}'.format(test_4kib_write),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(write_4kib_median),
                          'custom_stdev': int(write_4kib_stdev),
                          'custom_baseline_throughput': int(base_write_4kib_median),
                          'custom_baseline_stdev': int(base_write_4kib_stdev)})
client.send_post('add_result/{}'.format(test_16mib_read),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(read_16mib_median),
                          'custom_stdev': int(read_16mib_stdev),
                          'custom_baseline_throughput': int(base_read_16mib_median),
                          'custom_baseline_stdev': int(base_read_16mib_stdev)})
client.send_post('add_result/{}'.format(test_16mib_write),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(write_16mib_median),
                          'custom_stdev': int(write_16mib_stdev),
                          'custom_baseline_throughput': int(base_write_16mib_median),
                          'custom_baseline_stdev': int(base_write_16mib_stdev)})
client.send_post('add_result/{}'.format(test_latency_10ms),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(latency_10iops),
                          'custom_baseline_throughput': int(base_latency_10iops)})
client.send_post('add_result/{}'.format(test_latency_30ms),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(latency_30iops),
                          'custom_baseline_throughput': int(base_latency_30iops)})
client.send_post('add_result/{}'.format(test_latency_100ms),
                         {'status_id': int(status), 'comment': str(comment), 'version': str(version), 'custom_throughput': int(latency_100iops),
                          'custom_baseline_throughput': int(base_latency_100iops)})
