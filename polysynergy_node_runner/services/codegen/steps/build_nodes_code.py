from polysynergy_node_runner.execution_context.flow_state import FlowState

from polysynergy_node_runner.services.codegen.steps.get_version_suffix import get_version_suffix


def build_nodes_code(nodes: list, groups_with_output: set):
    lines = []
    for nd in nodes:
        is_group = nd.get("type") == "group"
        # If it's a group that has no output, skip it.
        if is_group and nd["id"] not in groups_with_output:
            continue
        if is_group:
            class_name = f"GroupNode_{nd['id'].replace('-', '_')}" if is_group else "UnknownClass"
        else:
            code = nd.get("code", "")
            class_name = "UnknownClass"
            if "@node" in code:
                after = code.split("@node", 1)[-1]
                if "class" in after:
                    after2 = after.split("class", 1)[-1]
                    base_class_name = after2.split("(")[0].strip() or "UnknownClass"
                    version = nd.get("version", 0.0)

                    version_suffix = get_version_suffix(version)
                    class_name = f"{base_class_name}{version_suffix}"

        var_name = "            node_" + nd["id"].replace("-", "_")
        factory_method_name = "make_" + var_name.strip() + "_instance(node_context)"
        lines.append(f"\n        def {factory_method_name}:")

        stateful = nd.get('stateful', True)
        lines.append(
            f"{var_name} = {class_name}(id='{nd['id']}', handle='{nd['handle']}', stateful={stateful}, context=node_context)")

        lines.append(f"            def factory():")
        lines.append(f"                return {factory_method_name}")

        lines.append(f"{var_name}.factory = factory")

        if not is_group:
            lines.append(f"{var_name}.path = '{nd['path']}'")
        else:
            lines.append(f"{var_name}.path = 'group'")

        if "flowState" in nd:
            flow_state_enum = next(
                (f"FlowState.{state.name}" for state in FlowState if state.value == nd['flowState']), None)

            if flow_state_enum is None:
                flow_state_enum = "FlowState.ENABLED"

            lines.append(f"{var_name}.flow_state = {flow_state_enum}")

        for v in nd.get("variables", []):
            handle = v["handle"]
            tp = v["type"]
            val = v["value"]

            if (
                    isinstance(val, list)
                    and val
                    and all(isinstance(item, dict) and "handle" in item and "value" in item for item in val)
            ):
                transformed_val = {item["handle"]: item["value"] for item in val}
                val_repr = repr(transformed_val)

            elif val == {} and any(t.strip() == "list" for t in tp.split("|")):
                val_repr = "[]"

            elif val == {} and any(t.strip() == "dict" for t in tp.split("|")):
                val_repr = "{}"

            else:
                val_repr = repr(val)

            if tp == "true_path":
                lines.append(f"{var_name}.true_path = {bool(val)}")
            elif tp == "false_path":
                lines.append(f"{var_name}.false_path = {bool(val)}")
            else:
                lines.append(f"{var_name}.{handle} = {val_repr}")

        lines.append(f"{var_name}.set_driving_connections(get_driving_connections(connections, '{nd['id']}'))")
        lines.append(f"{var_name}.set_in_connections(get_in_connections(connections, '{nd['id']}'))")
        lines.append(f"{var_name}.set_out_connections(get_out_connections(connections, '{nd['id']}'))")
        lines.append(f"            return {var_name.strip()}")

        lines.append(
            f"\n        if mock or '{nd['category']}' != 'mock': state.register_node(make_{var_name.strip()}_instance(node_context))")
        lines.append(f"\n")

    return "\n".join(lines)