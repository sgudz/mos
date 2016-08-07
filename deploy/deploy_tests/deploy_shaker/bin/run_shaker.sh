#!/usr/bin/env bash

SHAKER=`which shaker`
SHAKER_IMAGE_BUILDER=`which shaker-image-builder`

cd ${SCENARIOS_DIR}
SCENARIOS=`find ${SCENARIOS_NAMES} \( -name "*.json" -or -name "*.yaml" \) | uniq`
cd -

if (( $? != 0 )); then
    echo "ERROR: Can't find scenarios, check again!!!"
fi

${SHAKER_IMAGE_BUILDER}

for SCENARIO in ${SCENARIOS}; do
    BASENAME=$(basename -s .json -s .yaml ${SCENARIO})

    echo ${BASENAME}

    ${SHAKER} \
        --debug \
        --server-endpoint ${SERVER_ENDPOINT} \
        --scenario ${SCENARIOS_DIR}/$SCENARIO \
        --report ${ARTIFACTS_DIR}/${BASENAME}.html \
        --output ${ARTIFACTS_DIR}/${BASENAME}.json \
        --subunit ${ARTIFACTS_DIR}/${BASENAME}.subunit \
        --log-file ${ARTIFACTS_DIR}/${BASENAME}.log
done
