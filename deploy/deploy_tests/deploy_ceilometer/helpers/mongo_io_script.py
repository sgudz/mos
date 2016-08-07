import argparse
import time

import pymongo


def main():
    parser = argparse.ArgumentParser(
        description='generate metering data',
    )
    parser.add_argument('url')
    parser.add_argument('interval', type=int)
    parser.add_argument('nodename')

    args = parser.parse_args()
    client = pymongo.MongoClient(args.url)
    interval = int(args.interval)
    nodename = args.nodename
    docs_count = None
    for i in range(1, 100000):
        time.sleep(interval)
        if not docs_count:
            docs_count = client.ceilometer.meter.count()
        else:
            curr_count = client.ceilometer.meter.count()
            log = open('/tmp/ceilometer_logs/{nodename}-mongoio.log'.format(
                nodename=nodename), 'aw')
            log.write('%s %s\n' %
                      (int(time.time()), (curr_count - docs_count) / interval))
            log.close()
            docs_count = curr_count

if __name__ == '__main__':
    main()
