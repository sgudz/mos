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
test_4kib_read = test_4kib_write = test_16mib_read = test_16mib_write = test_latency_10_ms = test_latency_30_ms = test_latency_100_ms = None
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

### Actual data
read_16mib_median = int(dict(parser.items('testrail'))['read_16mib_median'])
read_16mib_stdev = int(dict(parser.items('testrail'))['read_16mib_stdev'])
write_16mib_median = int(dict(parser.items('testrail'))['write_16mib_median'])
write_16mib_stdev = int(dict(parser.items('testrail'))['write_16mib_stdev'])
read_4kib_median = int(dict(parser.items('testrail'))['read_4kib_median'])
read_4kib_stdev = int(dict(parser.items('testrail'))['read_4kib_stdev'])
write_4kib_median = int(dict(parser.items('testrail'))['write_4kib_median'])
write_4kib_stdev = int(dict(parser.items('testrail'))['write_4kib_stdev'])

latency_10_ms = dict(parser.items('testrail'))['latency_10_ms']
latency_30_ms = dict(parser.items('testrail'))['latency_30_ms']
latency_100_ms = dict(parser.items('testrail'))['latency_100_ms']

print latency_10_ms, latency_30_ms, latency_100_ms
print type(latency_10_ms), type(latency_30_ms), type(latency_100_ms)
### Default status
read_16mib_glob_status = read_16mib_custom_status = 1
read_4kib_glob_status = read_4kib_custom_status = 1
write_16mib_glob_status = write_16mib_custom_status = 1
write_4kib_glob_status = write_4kib_custom_status = 1
latency_10_ms_glob_status = latency_10_ms_custom_status = 1
latency_30_ms_glob_status = latency_30_ms_custom_status = 1
latency_100_ms_glob_status = latency_100_ms_custom_status = 1

### Define status for tests, based on Baseline - 20%
if read_16mib_median < float(base_read_16mib_median) * 0.8:
    read_16mib_glob_status = read_16mib_custom_status = 5
if read_4kib_median < float(base_read_4kib_median) * 0.8:
    read_4kib_glob_status = read_4kib_custom_status = 5
if write_16mib_median < float(base_write_16mib_median) * 0.8:
    write_16mib_glob_status = write_16mib_custom_status = 5
if write_4kib_median < float(base_write_4kib_median) * 0.8:
    write_4kib_glob_status = write_4kib_custom_status = 5
if latency_10_ms < float(base_latency_10_ms) * 0.8:
    latency_10_ms_glob_status = latency_10_ms_custom_status = 5
if latency_30_ms < float(base_latency_30_ms) * 0.8:
    latency_30_ms_glob_status = latency_30_ms_custom_status = 5
if latency_100_ms < float(base_latency_100_ms) * 0.8:
    latency_100_ms_glob_status = latency_100_ms_custom_status = 5

### Custom results for tests
custom_res_4kib_read = [{'status_id': read_4kib_custom_status, 'content': 'Check [Operations per second Median; iops]',
                         'expected': str(base_read_4kib_median), 'actual': str(read_4kib_median)},
                        {'status_id': 1, 'content': 'Check [deviation; %]', 'expected': str(base_read_4kib_stdev),
                         'actual': str(read_4kib_stdev)}]
custom_res_4kib_write = [{'status_id': write_4kib_custom_status, 'content': 'Check [Operations per second Median; iops]',
                        'expected': str(base_write_4kib_median),
                         'actual': str(write_4kib_median)},
                        {'status_id': 1, 'content': 'Check [deviation; %]', 'expected': str(base_write_4kib_stdev),
                         'actual': str(write_4kib_stdev)}]
custom_res_16mib_read = [{'status_id': read_16mib_custom_status, 'content': 'Check [bandwidth Median; MiBps]',
                         'expected': str(base_read_16mib_median),
                         'actual': str(read_16mib_median)},
                        {'status_id': 1, 'content': 'Check [deviation; %]', 'expected': str(base_read_16mib_stdev),
                         'actual': str(read_16mib_stdev)}]
custom_res_16mib_write = [{'status_id': write_16mib_custom_status, 'content': 'Check [bandwidth Median; MiBps]',
                         'expected': str(base_write_16mib_median),
                         'actual': str(write_16mib_median)},
                        {'status_id': 1, 'content': 'Check [deviation; %]', 'expected': str(base_write_16mib_stdev),
                         'actual': str(write_16mib_stdev)}]
custom_res_latency_10 = [{'status_id': latency_10_ms_custom_status, 'content': 'Check [operation per sec, iops]',
                        'expected': str(base_latency_10_ms), 'actual': str(latency_10_ms)}]
custom_res_latency_30 = [{'status_id': latency_30_ms_custom_status, 'content': 'Check [operation per sec, iops]',
                        'expected': str(base_latency_30_ms), 'actual': str(latency_30_ms)}]
custom_res_latency_100 = [{'status_id': latency_100_ms_custom_status, 'content': 'Check [operation per sec, iops]',
                        'expected': str(base_latency_100_ms), 'actual': str(latency_100_ms)}]

### Global results for tests
res_4kib_read = {'test_id': test_4kib_read, 'status_id': read_4kib_glob_status, 'version': str(version),
                 'custom_test_case_steps_results': custom_res_4kib_read}
res_4kib_write = {'test_id': test_4kib_write, 'status_id': write_4kib_glob_status, 'version': str(version),
                  'custom_test_case_steps_results': custom_res_4kib_write}
res_16mib_read = {'test_id': test_16mib_read, 'status_id': read_16mib_glob_status, 'version': str(version),
                  'custom_test_case_steps_results': custom_res_16mib_read}
res_16mib_write = {'test_id': test_16mib_write, 'status_id': write_16mib_glob_status, 'version': str(version),
                   'custom_test_case_steps_results': custom_res_16mib_write}
res_latency_10 = {'test_id': test_latency_10_ms, 'status_id': latency_10_ms_glob_status, 'version': str(version),
                  'custom_test_case_steps_results': custom_res_latency_10}
res_latency_30 = {'test_id': test_latency_30_ms, 'status_id': latency_30_ms_glob_status, 'version': str(version),
                  'custom_test_case_steps_results': custom_res_latency_30}
res_latency_100 = {'test_id': test_latency_100_ms, 'status_id': latency_100_ms_glob_status, 'version': str(version),
                   'custom_test_case_steps_results': custom_res_latency_100}
### List of global results
results_list = [res_4kib_read, res_4kib_write, res_16mib_read, res_16mib_write, res_latency_10, res_latency_30,
                res_latency_100]

### forming dict for testrail with all results
results_all_dict = {'results': results_list}

### Pushing all resalts to testrail
client.send_post('add_results/{}'.format(run_id), results_all_dict)
