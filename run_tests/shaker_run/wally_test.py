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
run_id = 18466
def get_tests_ids():
    tests = client.send_get('get_tests/{}'.format(run_id))
    tests_ids = []
    test_names = {}
    for item in tests:
        tests_ids.append(item['id'])
        test_names[item['title']] = item['id']
    return test_names

list_t = get_tests_ids()
for item in list_t.keys():
        if "4 KiB blocks; Read" in item:
                test_4kib_read = list_t[item]
        elif "4 KiB blocks; Write" in item:
                test_4kib_write = list_t[item]
        elif "16MiB blocks; Read":
                test_16mib_read = list_t[item]
        elif "16MiB blocks; Write":
                test_16mib_write = list_t[item]
        elif "latency 10ms" in item:
                test_latency_10ms = list_t[item]
        elif "latency 30ms" in item:
                test_latency_30ms = list_t[item]
        elif "latency 100ms" in item:
                test_latency_100ms = list_t[item]
print test_4kib_read, test_4kib_write, test_16mib_read, test_16mib_write, test_latency_10ms, test_latency_30ms, test_latency_100ms
