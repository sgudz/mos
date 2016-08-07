# coding: utf-8
from yaml import load as yaml_load


def flat_resultset(result_set):
    """Combinate tags and value in single dict

    :param: result_set Response from influxdb query
    :return: generator combinations data values and tag
    """
    for serie in result_set._get_series():
        tags = serie.get('tags', {})

        for el in result_set._get_points_for_serie(serie):
            item = tags.copy()
            item.update(el)
            yield item


def parse_astute(astute_yaml):
    """Pars astute.yaml and get what we need.

    :param astute_yaml: str path to fuel astute.yml file, that contains
    info about cluster nodes.
    :return:
    """
    with open(astute_yaml, "r") as f:
        astute = yaml_load(f)
    roles = {"controller": {"count": 0, "nodes": []},
             "compute": {"count": 0, "nodes": []},
             "compute_osd": {"count": 0, "nodes": []},
             "osd": {"count": 0, "nodes": []}}

    for _, node in astute["network_metadata"]["nodes"].iteritems():
        node_roles = node["node_roles"]
        node_rst_role = ""
        if len(node_roles) == 1:
            role = node_roles[0]
            if role in ["controller", "primary-controller"]:
                node_rst_role = "controller"
            if role == "compute":
                node_rst_role = "compute"
            if role == "ceph-osd":
                node_rst_role = "osd"
        elif (len(node_roles) == 2 and "compute" in node_roles and
              "ceph-osd" in node_roles):
            node_rst_role = "compute_osd"

        roles[node_rst_role]["count"] += 1
        roles[node_rst_role]["nodes"].append(
            {"name": node["name"],
             "ip": node["network_roles"]["management"]})

    return roles
