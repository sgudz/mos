set -ex
SERVERS="185.8.59.227 185.8.59.228 185.8.59.229 185.8.59.251 185.8.59.252 185.8.59.253 185.8.59.254 185.8.58.254"

for i in ${SERVERS}; do
        /usr/bin/ipmitool -H $i -U engineer -P i1LwPKhqzAR0 power reset ;
done
