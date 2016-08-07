import yaml
import sys

astute_yaml_file = "astute.yaml"

with open(astute_yaml_file, 'r') as stream:
    try:
        cfg = yaml.load(stream)
        if sys.argv[1] == "all":
            print(cfg)
        if sys.argv[1] == "mgmt_vip":
            print(cfg['network_metadata']['vips']['management']['ipaddr'])
        if sys.argv[1] == "influxdb_address":
            if cfg['lma_collector']['influxdb_address']:
                print(cfg['lma_collector']['influxdb_address'])
        if sys.argv[1] == "lma_label":
            if cfg['lma_collector']['environment_label']:
                print(cfg['lma_collector']['environment_label'])
        if sys.argv[1] == "user":
            print(cfg['access']['user'])
        if sys.argv[1] == "tenant":
            print(cfg['access']['tenant'])
        if sys.argv[1] == "password":
            print(cfg['access']['password'])
        if sys.argv[1] == "ext_net":
            print(cfg['quantum_settings']['predefined_networks'][
                'admin_floating_net']['L3']['subnet'])
        if sys.argv[1] == "computes_count":
            computes_count = 0
            for node in cfg['network_metadata']['nodes']:
                for node_role in cfg['network_metadata']['nodes'][node][
                        'node_roles']:
                    if node_role == 'compute':
                        computes_count = computes_count + 1
            print(computes_count)
    except yaml.YAMLError as exc:
        print(exc)
