import string
from collections import defaultdict


def build_group_nodes_code(conns_data: list, groups_with_output: set) -> str:
    group_conn_map = defaultdict(list)

    for conn in conns_data:
        tgt_node = conn.get("targetNodeId")
        tgt_group = conn.get("targetGroupId")

        if tgt_node and tgt_group and tgt_node == tgt_group:
            group_conn_map[tgt_group].append(conn)

    lines = []

    for group_id, conns in group_conn_map.items():

        # Skip group with no output
        if group_id not in groups_with_output:
            continue

        prefix_map = {}
        current_index = 0
        group_lines = []
        class_name = f"GroupNode_{group_id.replace('-', '_')}"

        group_lines.append(f"class {class_name}(ExecutableNode):")

        for conn in conns:
            src_id = conn["sourceNodeId"]
            src_handle = conn["sourceHandle"]
            tgt_handle = conn["targetHandle"]

            if src_id not in prefix_map:
                prefix_map[src_id] = string.ascii_lowercase[current_index]
                current_index += 1

            prefix = prefix_map[src_id]
            prop_name = f"{prefix}_{src_handle}"
            group_lines.append(f"    {prop_name} = None  # from targetHandle {tgt_handle}")

        group_lines.append(f"    def execute(self):")
        group_lines.append(f"        pass")
        lines.append("\n".join(group_lines) + "\n")

    return "\n".join(lines)