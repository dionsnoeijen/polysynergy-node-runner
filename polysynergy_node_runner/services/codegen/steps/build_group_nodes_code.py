import string
from collections import defaultdict


def build_group_nodes_code(conns_data: list, groups_with_output: set) -> str:
    group_conn_map = defaultdict(list)

    for conn in conns_data:
        tgt_node = conn.get("targetNodeId")
        tgt_group = conn.get("targetGroupId")
        is_in_group = conn.get("isInGroup")

        # Match connections to group boundaries in two ways:
        # 1. Classic: targetNodeId == targetGroupId (both set)
        # 2. Nested groups: targetNodeId == isInGroup (targetGroupId not set)
        if tgt_node and tgt_group and tgt_node == tgt_group:
            group_conn_map[tgt_group].append(conn)
        elif tgt_node and is_in_group and tgt_node == is_in_group:
            group_conn_map[is_in_group].append(conn)

    lines = []

    for group_id, conns in group_conn_map.items():

        # Skip group with no output
        if group_id not in groups_with_output:
            continue

        prefix_map = {}
        current_index = 0
        group_lines = []
        properties = []  # Track all property names
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
            properties.append(prop_name)
            group_lines.append(f"    {prop_name} = None  # from targetHandle {tgt_handle}")

        # Group properties by prefix to handle true_path/false_path pairs
        prefix_props = defaultdict(dict)
        for prop in properties:
            if '_true_path' in prop:
                prefix = prop.split('_true_path')[0]
                prefix_props[prefix]['true_path'] = prop
            elif '_false_path' in prop:
                prefix = prop.split('_false_path')[0]
                prefix_props[prefix]['false_path'] = prop

        # Generate execute method with connection killing logic based on incoming connections
        group_lines.append(f"    def execute(self):")

        if not prefix_props:
            # No path properties, just pass
            group_lines.append(f"        pass")
        else:
            # Debug: print property values
            for prefix, props in sorted(prefix_props.items()):
                for path_type, prop_name in props.items():
                    group_lines.append(f"        print(f'  {prop_name} = {{self.{prop_name}}}')")

            # Debug: print incoming connection states
            group_lines.append(f"        for in_conn in self.get_in_connections():")
            group_lines.append(f"            print(f'  {{in_conn.source_handle}} -> {{in_conn.target_handle}}, killer={{in_conn.is_killer()}}')")

            # Mirror the incoming connection states to outgoing connections
            # If an incoming connection is killed, kill the corresponding outgoing connections
            # If a property has an error value (truthy for false_path), kill all except false_path
            group_lines.append(f"        for in_conn in self.get_in_connections():")
            group_lines.append(f"            if in_conn.is_killer():")
            group_lines.append(f"                # Incoming connection was killed, mirror this to outgoing connections")
            group_lines.append(f"                target_handle = in_conn.target_handle")
            group_lines.append(f"                for out_conn in self.get_out_connections():")
            group_lines.append(f"                    if out_conn.source_handle == target_handle:")
            group_lines.append(f"                        out_conn.make_killer()")

            # Add logic to handle error cases (false_path is truthy)
            for prefix, props in sorted(prefix_props.items()):
                false_path_prop = props.get('false_path')
                true_path_prop = props.get('true_path')

                if false_path_prop:
                    # If false_path has an error value (truthy), kill all except false_path
                    group_lines.append(f"        if self.{false_path_prop}:")
                    group_lines.append(f"            for connection in [c for c in self.get_out_connections() if c.source_handle != '{false_path_prop}']:")
                    group_lines.append(f"                connection.make_killer()")

                if true_path_prop:
                    # If true_path is explicitly False (not None), kill those connections
                    group_lines.append(f"        if self.{true_path_prop} is False:")
                    group_lines.append(f"            for connection in [c for c in self.get_out_connections() if c.source_handle == '{true_path_prop}']:")
                    group_lines.append(f"                connection.make_killer()")

        lines.append("\n".join(group_lines) + "\n")

    return "\n".join(lines)