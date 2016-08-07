FROM python:2.7

# Base dir
ENV BASE_DIR /data/shaker

# Specify artifacts dir for runtime generated data (logs, process results, etc)
ENV ARTIFACTS_DIR $BASE_DIR/artifacts

# Directory with scenarios in container
ENV SCENARIOS_DIR mos_scenarios

# Which scenarios need to run.
# Path relatively to SCENARIOS_PATH with scenario files
# Can be: string of dir and files separated by space.
ENV SCENARIOS_NAMES scenarios

# Server ip for remote shaker agents
ENV SERVER_IP 127.0.0.1

# Build project
RUN mkdir -p $BASE_DIR && mkdir -p $ARTIFACTS_DIR
WORKDIR $BASE_DIR

COPY . $BASE_DIR/

RUN pip install --no-cache-dir -r requirements.txt

VOLUME [$ARTIFACTS_DIR]
VOLUME [$SCENARIOS_DIR]

CMD ["make", "test"]
