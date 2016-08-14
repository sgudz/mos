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
base_read_16mib_median = dict(parser.items('testrail'))['base_read_16mib_median']
base_read_16mib_stdev = dict(parser.items('testrail'))['base_read_16mib_median']

list_t = get_tests_ids()
print list_t.keys()
for item in list_t.keys():
    if "16MiB" in item and "Read" in item and not "[deprecated]" in item:
        print list_t[item]
        print item
        client.send_post('add_result/{}'.format(list_t[item]),
                         {'status_id': 1, 'version': str(version), 'custom_throughput': int(read_16mib_median),
                          'custom_stdev': int(read_16mib_stdev),
                          'custom_baseline_throughput': int(base_read_16mib_median),
                          'custom_baseline_stdev': int(base_read_16mib_stdev)})
