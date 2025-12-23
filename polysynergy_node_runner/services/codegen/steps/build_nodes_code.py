import hashlib
import logging
import os
import re
from pathlib import Path
from importlib import import_module

from polysynergy_node_runner.execution_context.flow_state import FlowState
from polysynergy_node_runner.services.codegen.steps.get_version_suffix import get_version_suffix

logger = logging.getLogger(__name__)


def discover_node_code(node_data: dict) -> str:
    """
    Discover node code using path-based discovery with fallback to stored code.
    Uses NODE_PACKAGES env var to determine which packages are available.
    
    Args:
        node_data: Node configuration from JSON
        
    Returns:
        Node code (either from file system or stored fallback)
    """
    node_path = node_data.get("path")
    
    if node_path:
        try:
            # Check if this node is from an available package
            node_packages = os.getenv("NODE_PACKAGES", "").split(",")
            node_packages = [pkg.strip() for pkg in node_packages if pkg.strip()]
            
            # Check if the node path starts with any available package
            is_available_package = any(node_path.startswith(pkg) for pkg in node_packages)
            
            if is_available_package:
                # Try to discover the file without importing (to avoid dependency issues)
                # Remove the class name (last component) to get the module path
                module_path = ".".join(node_path.split(".")[:-1])
                file_path = module_path.replace(".", "/") + ".py"
                
                # Build search paths dynamically based on NODE_PACKAGES and common locations
                base_paths = [
                    Path.cwd().parent,  # Parent directory (development)
                    Path.cwd(),         # Current directory
                    Path("/app"),       # Docker /app location
                    Path("/"),          # Docker root (for /nodes, /nodes_agno, etc.)
                ]

                # Build search paths: for each base path, add package-specific subdirectories
                search_paths = []
                for base in base_paths:
                    # Add direct base path
                    search_paths.append(base)
                    # Add package-specific paths based on NODE_PACKAGES
                    # e.g., polysynergy_nodes -> nodes, polysynergy_nodes_agno -> nodes_agno
                    for pkg in node_packages:
                        if pkg.startswith("polysynergy_"):
                            # Convert package name to directory name
                            # polysynergy_nodes -> nodes
                            # polysynergy_nodes_agno -> nodes_agno
                            dir_name = pkg.replace("polysynergy_", "")
                            search_paths.append(base / dir_name)
                
                for base_path in search_paths:
                    potential_file = base_path / file_path
                    if potential_file.exists():
                        try:
                            with open(potential_file, 'r') as f:
                                live_code = f.read()
                            
                            # Optional: Check for hash differences and warn
                            if node_data.get("code_hash"):
                                current_hash = hashlib.sha256(live_code.encode()).hexdigest()
                                if current_hash != node_data.get("code_hash"):
                                    logger.warning(
                                        f"Node {node_data.get('type', 'unknown')} version differs from flow definition "
                                        f"(using local version)"
                                    )
                            
                            logger.debug(f"Successfully discovered live code for {node_data.get('type', 'unknown')} at {potential_file}")
                            return live_code
                            
                        except Exception as read_e:
                            logger.warning(f"Failed to read file {potential_file}: {read_e}")
                            continue
            else:
                logger.debug(f"Node {node_data.get('type', 'unknown')} from package not in NODE_PACKAGES, using stored code")
                    
        except Exception as e:
            logger.warning(f"Failed to discover code for {node_data.get('type', 'unknown')} at {node_path}: {e}")
    
    # Fallback to stored code
    stored_code = node_data.get("code", "")
    if not stored_code:
        logger.warning(f"No code found for node {node_data.get('type', 'unknown')} (no path or stored code)")
    
    return stored_code


def build_nodes_code(nodes: list, groups_with_output: set):
    lines = []

    # Add import for find_connected_component at the top of node building section
    lines.append("        from polysynergy_node_runner.execution_context.utils.traversal import find_connected_component")
    lines.append("")
    lines.append("        # Determine which nodes are connected to the execution flow")
    lines.append("        # Only register nodes that are reachable from trigger_node_id")
    lines.append("        if trigger_node_id:")
    lines.append("            connected_node_ids = find_connected_component(trigger_node_id, connections)")
    lines.append("        else:")
    lines.append("            # No trigger_node_id means register all nodes (backward compatibility)")
    lines.append("            connected_node_ids = None")
    lines.append("")
    # Add runtime debug logging
    lines.append("        # Debug: Show runtime node filtering info")
    lines.append("        print(f'[RUNTIME] trigger_node_id: {trigger_node_id}')")
    lines.append("        print(f'[RUNTIME] Total connections built: {len(connections)}')")
    lines.append("        print(f'[RUNTIME] connected_node_ids: {connected_node_ids}')")
    lines.append("")

    for nd in nodes:
        node_type = nd.get("type")
        is_group = node_type == "group"
        is_warp_gate = node_type == "warp_gate"

        # Skip warp gates entirely (frontend-only visual nodes)
        if is_warp_gate:
            continue

        # If it's a group that has no output, skip it.
        if is_group and nd["id"] not in groups_with_output:
            continue
        if is_group:
            class_name = f"GroupNode_{nd['id'].replace('-', '_')}"
        else:
            # The path is the single source of truth for the class name
            node_path = nd.get('path', '')
            
            if not node_path:
                logger.error(
                    f"Node {nd.get('id')} has no path! This is a critical data error. "
                    f"Node type: {nd.get('type')}"
                )
                class_name = "UnknownClass"
            else:
                # Extract the class name from the path (last component)
                # e.g., 'polysynergy_nodes.variable.variable_string.VariableString' -> 'VariableString'
                base_class_name = node_path.split('.')[-1]
                
                # Add version suffix for the compiled version
                version = nd.get("version", 0.0)
                version_suffix = get_version_suffix(version)
                class_name = f"{base_class_name}{version_suffix}"
                
                logger.debug(
                    f"Node {nd.get('id')}: path={node_path}, "
                    f"extracted class={base_class_name}, "
                    f"versioned class={class_name}"
                )
            
            # Still need to discover code for inclusion in the generated file
            # But we don't use it for class name extraction
            code = discover_node_code(nd)

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

        # Handle hook-generated attributes (keys starting with underscore)
        for key, value in nd.items():
            if key.startswith('_') and not key.startswith('__'):
                lines.append(f"{var_name}.{key} = {repr(value)}")

        lines.append(f"{var_name}.set_driving_connections(get_driving_connections(connections, '{nd['id']}'))")
        lines.append(f"{var_name}.set_in_connections(get_in_connections(connections, '{nd['id']}'))")
        lines.append(f"{var_name}.set_out_connections(get_out_connections(connections, '{nd['id']}'))")
        lines.append(f"            return {var_name.strip()}")

        # Register node only if it's connected to the execution flow (or if no filtering is enabled)
        lines.append(f"\n        if mock or '{nd['category']}' != 'mock':")
        lines.append(f"            if connected_node_ids is None or '{nd['id']}' in connected_node_ids:")
        lines.append(f"                state.register_node(make_{var_name.strip()}_instance(node_context))")
        lines.append(f"\n")

    return "\n".join(lines)