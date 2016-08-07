#!/bin/bash -e
set +x
MAX_TIME=$((60*60*24))
TIME=0
LEFT=${MAX_TIME}
while true; do
   echo "Reserved by ${BUILD_USER} left $LEFT seconds"
   sleep 600
   TIME=$((${TIME}+600))
   LEFT=$((${MAX_TIME}-${TIME}))
   if [ "${TIME}" -ge "${LEFT}" ] ; then
        echo "Reservation timeout"
        exit
   fi
done
