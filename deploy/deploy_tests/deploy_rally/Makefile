CURRENT_DIRECTORY := $(shell pwd)
VENV_DIR = $(CURRENT_DIRECTORY)/virtualenv
RALLY = $(VENV_DIR)/bin/rally
PYTHON = $(VENV_DIR)/bin/python

test: create_deployment run_tests generate_reports

create_deployment:
	-$(RALLY) deployment create --no-use --filename $(DEPLOYMENT_CONFIG) --name $(DEPLOYMENT_NAME)
	$(RALLY) deployment use $(DEPLOYMENT_NAME)

run_tests:
	@if [ $(DB_CONNECTION) ] && [ $(DB_CONNECTION) != "" ]; then \
		sed -i "s|connection *=.*|connection = ${DB_CONNECTION}|" $(VENV_DIR)/etc/rally/rally.conf; \
	fi
	-sh ./bin/run_rally.sh

generate_reports:
	$(eval TASK_LIST := $(shell $(RALLY) task list --uuids-only))
	$(RALLY) task report --tasks $(TASK_LIST) --out=./artifacts/rally_report.html
	$(RALLY) task report --tasks $(TASK_LIST) --out=./artifacts/rally_report.xml --junit

	# generate rally reports from influxDB
	-$(PYTHON) -m rally_reports --influxdb-connection=$(INFLUXDB_CONNECTION) \
	    --html-file=$(ARTIFACTS_DIR)/report.html \
	    --rst-file=$(ARTIFACTS_DIR)/report.rst \
	    --rst-report-type=$(RST_REPORT_TYPE) \
	    --astute-yaml=$(ASTUTE_YAML_FILE) \
	    --deployment=$(DEPLOYMENT_NAME)

# format: make build-docker mysql+pymysql://user:pass@localhost/dbname
build_docker:
ifndef DB_CONNECTION
	$(error DB_CONNECTION is not set)
endif

ifndef RALLY_IMAGE_NAME
	$(error RALLY_IMAGE_NAME is not set)
endif
	sudo docker build --build-arg DB_CONNECTION=$(DB_CONNECTION) -t $(RALLY_IMAGE_NAME) ./
	sudo docker push $(RALLY_IMAGE_NAME)
