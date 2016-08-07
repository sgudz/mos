test: disable_quotas run_tests

build_docker:
ifndef SHAKER_IMAGE_NAME
	$(error SHAKER_IMAGE_NAME is not set)
endif
	sudo docker build -t $(SHAKER_IMAGE_NAME) ./
	sudo docker push $(SHAKER_IMAGE_NAME)

QUOTAS = floating-ips networks ports routers secgroups secgroup-rules subnets ram cores instances
disable_quotas:
	$(eval OS_TENANT_ID := $(shell openstack project show $(OS_TENANT_NAME) -c id -f value))
	$(foreach var,$(QUOTAS),openstack quota set --$(var) -1 $(OS_TENANT_ID);)

	openstack quota show

run_tests:
	-sh ./bin/run_shaker.sh
