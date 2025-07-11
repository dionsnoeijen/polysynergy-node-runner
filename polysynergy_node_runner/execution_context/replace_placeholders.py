import json
import traceback
from jinja2 import Environment, StrictUndefined
from jinja2.ext import Extension

# Setup Jinja2 environment
jinja_env = Environment(undefined=StrictUndefined)
jinja_env.filters['tojson'] = json.dumps

def replace_placeholders(data, values: dict = None, state=None):
    """
    data: string, dict of list met {{ placeholders }}
    values: lokale dict
    state: ExecutionState, met toegang tot andere nodes
    """
    context = dict(values or {})

    if state:
        for handle, node in state.nodes_by_handle.items():
            node_dict = node.to_dict()
            context[handle] = node_dict
            context[handle].setdefault("true_path", getattr(node, "true_path", None))
            context[handle + "__default__"] = getattr(node, "true_path", None)

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

def _render_template_string(template_str: str, context: dict) -> str:
    template = jinja_env.from_string(template_str)
    return template.render(context)