import re
try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

data = open('/root/ceph_report.html')
structure = str(data.readlines())
soup = BeautifulSoup(structure, 'html.parser')
tables1 = str(soup.find_all(class_="table table-bordered table-striped")[1])
tables2 = str(soup.find_all(class_="table table-bordered table-striped")[2])
tables3 = str(soup.find_all(class_="table table-bordered table-striped")[3])
soup1 = BeautifulSoup(tables1, 'html.parser')
soup2 = BeautifulSoup(tables2, 'html.parser')
soup3 = BeautifulSoup(tables3, 'html.parser')
rrd4k_data = soup1.find_all('td')[3].string
rwd4k_data = soup1.find_all('td')[5].string
rrd16MiB_data = soup2.find_all('td')[3].string
rwd16MiB_data = soup2.find_all('td')[5].string

try:
        rws10ms_data = int(soup3.find_all('td')[3].string)
except ValueError:
        rws10ms_data = 0
try:
        rws30ms_data = int(soup3.find_all('td')[5].string)
except ValueError:
        rws30ms_data = 0
rws100ms_data = int(soup3.find_all('td')[7].string[2:])

rrd4k_iops = int(re.findall(r"[\d']+", rrd4k_data)[0])
rwd4k_iops = int(re.findall(r"[\d']+", rwd4k_data)[0])
rrd16MiB_bandwidth = int(re.findall(r"[\d']+", rrd16MiB_data)[0])
rwd16MiB_bandwidth = int(re.findall(r"[\d']+", rwd16MiB_data)[0])

rrd4k_dev = int(re.findall(r"[\d']+", rrd4k_data)[-1])
rwd4k_dev = int(re.findall(r"[\d']+", rwd4k_data)[-1])
rrd16MiB_dev = int(re.findall(r"[\d']+", rrd16MiB_data)[-1])
rwd16MiB_dev = int(re.findall(r"[\d']+", rwd16MiB_data)[-1])


print "rrd4k_iops = {}".format(rrd4k_iops), "Dev : {}".format(rrd4k_dev)
print "rwd4k_iops = {}".format(rwd4k_iops), "Dev : {}".format(rwd4k_dev)
print "rrd16MiB_bandwidth = {}".format(rrd16MiB_bandwidth), "Dev : {}".format(rrd16MiB_dev)
print "rwd16MiB_bandwidth = {}".format(rwd16MiB_bandwidth), "Dev : {}".format(rwd16MiB_dev)

print "lat_10_iops : {}, lat_30_iops : {}, lat_100_iops : {}".format(rws10ms_data, rws30ms_data, rws100ms_data)
