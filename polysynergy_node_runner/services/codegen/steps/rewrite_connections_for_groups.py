import string
from collections import defaultdict


def rewrite_connections_for_groups(conns_data: list) -> None:

    group_inputs = defaultdict(list)

    for conn in conns_data:
        if (
            conn.get("targetNodeId") == conn.get("targetGroupId")
            and conn.get("targetNodeId") is not None
        ):
            group_inputs[conn["targetNodeId"]].append(conn)

    group_prefix_map = {}  # group_id -> {sourceNodeId: prefix}
    group_target_map = {}  # group_id -> {targetHandle: newHandle}

    for group_id, connections in group_inputs.items():
        prefix_map = {}
        target_map = {}
        current_index = 0

        for conn in connections:
            source_id = conn["sourceNodeId"]
            source_handle = conn["sourceHandle"]
            target_handle = conn["targetHandle"]

            if source_id not in prefix_map:
                prefix_map[source_id] = string.ascii_lowercase[current_index]
                current_index += 1

            prefix = prefix_map[source_id]
            # Replace dots with underscores to create valid Python property names
            sanitized_handle = source_handle.replace(".", "_")
            new_handle = f"{prefix}_{sanitized_handle}"
            target_map[target_handle] = new_handle

        group_prefix_map[group_id] = prefix_map
        group_target_map[group_id] = target_map

    for conn in conns_data:
        if (
                conn.get("targetNodeId") == conn.get("targetGroupId")
                and conn["targetGroupId"] in group_target_map
        ):
            tgt_group = conn["targetGroupId"]
            tgt_handle = conn["targetHandle"]
            conn["targetHandle"] = group_target_map[tgt_group].get(tgt_handle, tgt_handle)

        elif (
                conn.get("sourceGroupId") == conn.get("sourceNodeId")
                or conn.get("sourceGroupId")
        ):
            group_id = conn["sourceGroupId"]
            source_id = conn["sourceNodeId"]
            source_handle = conn["sourceHandle"]

            if group_id in group_prefix_map and source_id in group_prefix_map[group_id]:
                prefix = group_prefix_map[group_id][source_id]
                conn["sourceNodeId"] = group_id
                # Replace dots with underscores to create valid Python property names
                sanitized_handle = source_handle.replace(".", "_")
                conn["sourceHandle"] = f"{prefix}_{sanitized_handle}"
