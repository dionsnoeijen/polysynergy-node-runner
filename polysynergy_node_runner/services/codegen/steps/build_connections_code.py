def build_connections_code(connections, nodes, groups_with_output: set):
    lines = []
    node_dict = {nd["id"]: nd for nd in nodes}

    # Debug: Count connections being built
    built_count = 0
    skipped_group_internal = 0
    skipped_group_no_output = 0

    print(f"[CODEGEN-CONN] Total connections in JSON: {len(connections)}")
    print(f"[CODEGEN-CONN] Total nodes in JSON: {len(nodes)}")

    for c in connections:
        source_node = node_dict.get(c["sourceNodeId"], {})
        source_category = source_node.get("category", "")

        if (
            c.get("sourceNodeId") == c.get("sourceGroupId") and
            c.get("isInGroup") == c.get("sourceGroupId")
        ):
            skipped_group_internal += 1
            continue

        if source_category == 'group' and c["sourceNodeId"] not in groups_with_output:
            skipped_group_no_output += 1
            continue

        built_count += 1
        condition = f"mock or '{source_category}' != 'mock'"

        lines.append(
            f"        if {condition}: connections.append(Connection(uuid='{c['id']}', "
            f"source_node_id='{c['sourceNodeId']}', source_handle='{c['sourceHandle']}', "
            f"target_node_id='{c['targetNodeId']}', target_handle='{c['targetHandle']}', context=connection_context))"
        )

    print(f"[CODEGEN-CONN] Built: {built_count}, Skipped (group internal): {skipped_group_internal}, Skipped (group no output): {skipped_group_no_output}")

    return "\n".join(lines)