import json
import re
from jinja2 import Environment, StrictUndefined
from polysynergy_node_runner.execution_context.utils.traversal import find_node_by_handle_backwards

# Global context for backwards lookup (set during template rendering)
_backwards_context = {
    'state': None,
    'current_node': None
}

def set_backwards_context(state, current_node):
    """Set the context for backwards lookup during template rendering"""
    _backwards_context['state'] = state
    _backwards_context['current_node'] = current_node

def clear_backwards_context():
    """Clear the backwards lookup context"""
    _backwards_context['state'] = None
    _backwards_context['current_node'] = None

# Custom Jinja2 global function for backwards lookup
def backwards_lookup(handle):
    """Jinja2 global function to lookup handles backwards if not found locally"""
    state = _backwards_context['state']
    current_node = _backwards_context['current_node']

    if not state or not current_node:
        raise ValueError(f"Handle '{handle}' not found and no backwards context available")

    # Try backwards traversal
    found_node = find_node_by_handle_backwards(
        start_node=current_node,
        target_handle=handle,
        get_node_by_id=state.get_node_by_id
    )

    if found_node:
        node_dict = found_node.to_dict()
        node_dict.setdefault("true_path", getattr(found_node, "true_path", None))
        return node_dict

    raise ValueError(f"Handle '{handle}' not found in backwards traversal")

def _find_missing_handles_in_template(data, context):
    """
    Find handles referenced in templates that are missing from context.
    Looks for patterns like {{ handle.property }} and {{ handle }}.
    """
    if isinstance(data, str):
        template_str = data
    else:
        # Convert to JSON string to find templates in complex data structures
        template_str = json.dumps(data)

    # Find all Jinja2 variable references: {{ variable.property }} or {{ variable }}
    # Pattern matches: word characters followed by optional dot notation
    pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\.[a-zA-Z0-9_]+)*\s*\}\}'
    matches = re.findall(pattern, template_str)

    # Return handles that are not in context
    missing_handles = []
    for handle in matches:
        if handle not in context:
            missing_handles.append(handle)

    return list(set(missing_handles))  # Remove duplicates

# Setup Jinja2 environment
jinja_env = Environment(undefined=StrictUndefined)
jinja_env.filters['tojson'] = json.dumps

def replace_placeholders(data, values: dict = None, state=None, current_node=None):
    """
    data: string, dict of list met {{ placeholders }}
    values: lokale dict
    state: ExecutionState, met toegang tot andere nodes
    current_node: ExecutableNode, voor backwards traversal als handle niet gevonden
    """
    context = dict(values or {})

    # Set backwards context for global access during template rendering
    if state and current_node:
        set_backwards_context(state, current_node)

    try:
        if state:
            # Add all known nodes to context (original behavior)
            for handle, node in state.nodes_by_handle.items():
                node_dict = node.to_dict()
                context[handle] = node_dict
                context[handle].setdefault("true_path", getattr(node, "true_path", None))
                context[handle + "__default__"] = getattr(node, "true_path", None)

            # If we have current_node, try to pre-populate missing handles via backwards lookup
            if current_node:
                missing_handles = _find_missing_handles_in_template(data, context)
                for missing_handle in missing_handles:
                    try:
                        found_node = find_node_by_handle_backwards(
                            start_node=current_node,
                            target_handle=missing_handle,
                            get_node_by_id=state.get_node_by_id
                        )
                        if found_node and found_node != current_node:  # Don't use self as source
                            node_dict = found_node.to_dict()
                            node_dict.setdefault("true_path", getattr(found_node, "true_path", None))
                            context[missing_handle] = node_dict
                            context[missing_handle + "__default__"] = getattr(found_node, "true_path", None)
                    except Exception:
                        # If backwards lookup fails, skip this handle (will cause template error as expected)
                        pass

        # Als het al een string is: direct renderen
        if isinstance(data, str):
            return _render_template_string(data, context)

        # Anders: JSON dump → render → JSON load
        try:
            json_str = json.dumps(data)
            rendered = _render_template_string(json_str, context)
            return json.loads(rendered)
        except Exception as e:
            raise ValueError(f"Template rendering failed: {str(e)}")
    finally:
        # Always clear backwards context after rendering
        clear_backwards_context()

def _render_template_string(template_str: str, context: dict) -> str:
    template = jinja_env.from_string(template_str)
    return template.render(context)