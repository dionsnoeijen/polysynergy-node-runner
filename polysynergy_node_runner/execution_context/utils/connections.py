def get_driving_connections(connections: list, node_id: str):
    return [c for c in connections if
            c.target_node_id == node_id and c.target_handle in "node"]


def get_in_connections(connections: list, node_id: str):
    return [c for c in connections if c.target_node_id == node_id and c.target_handle not in "node"]


def get_alive_in_connections(connections: list, node_id: str):
    return [
        c for c in connections
        if c.target_node_id == node_id
           and c.target_handle not in "node"
           and not c.is_killer()
    ]


def get_out_connections(connections, node_id):
    return [c for c in connections if c.source_node_id == node_id]
