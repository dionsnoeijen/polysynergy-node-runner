def build_connections_code(connections, nodes, groups_with_output: set):
    lines = []
    node_dict = {nd["id"]: nd for nd in nodes}

    for c in connections:
        source_node = node_dict.get(c["sourceNodeId"], {})
        source_category = source_node.get("category", "")

        if (
            c.get("sourceNodeId") == c.get("sourceGroupId") and
            c.get("isInGroup") == c.get("sourceGroupId")
        ):
            continue

        if source_category == 'group' and c["sourceNodeId"] not in groups_with_output:
            continue

        condition = f"mock or '{source_category}' != 'mock'"  # Connection condition in gegenereerde code

        lines.append(
            f"    if {condition}: connections.append(Connection(uuid='{c['id']}', "
            f"source_node_id='{c['sourceNodeId']}', source_handle='{c['sourceHandle']}', "
            f"target_node_id='{c['targetNodeId']}', target_handle='{c['targetHandle']}'))"
        )

    return "\n".join(lines)