import json
import re
from jinja2 import Environment, StrictUndefined, BaseLoader, TemplateNotFound
from polysynergy_node_runner.execution_context.utils.traversal import find_node_by_handle_backwards

# Global project templates dict (set at code generation time)
_project_templates: dict = {}

def set_project_templates(templates: dict):
    """Set the project templates for Jinja extends support.

    This is called from generated code with templates embedded at compile time.
    """
    global _project_templates
    _project_templates = templates or {}


class ProjectTemplateLoader(BaseLoader):
    """Custom Jinja loader that loads templates from the project templates dict."""

    def get_source(self, environment, template):
        if template in _project_templates:
            source = _project_templates[template]
            # Return (source, filename, uptodate_func)
            # uptodate_func returns True since templates are static at runtime
            return source, template, lambda: True
        raise TemplateNotFound(template)


# Global context for template rendering (set during template rendering)
_template_context = {
    'state': None,
    'current_node': None,
    'components': None,
    'stage': None,
}

def set_template_context(state=None, current_node=None, components=None, stage=None):
    """Set the context for template rendering"""
    _template_context['state'] = state
    _template_context['current_node'] = current_node
    _template_context['components'] = components
    _template_context['stage'] = stage

def clear_template_context():
    """Clear the template rendering context"""
    _template_context['state'] = None
    _template_context['current_node'] = None
    _template_context['components'] = None
    _template_context['stage'] = None

# Legacy aliases for backwards compatibility
def set_backwards_context(state, current_node):
    set_template_context(state=state, current_node=current_node)

def clear_backwards_context():
    clear_template_context()


# Custom Jinja2 global function for backwards lookup
def backwards_lookup(handle):
    """Jinja2 global function to lookup handles backwards if not found locally"""
    state = _template_context['state']
    current_node = _template_context['current_node']

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


# Custom Jinja2 global function for rendering components
def component(key: str) -> str:
    """
    Jinja2 global function to render a connected component.

    Usage in templates: {{ component('table_users') }}
    """
    components = _template_context.get('components')
    if not components:
        return f"<!-- component('{key}'): No components available -->"

    comp = components.get(key)
    if comp and hasattr(comp, 'render'):
        return comp.render()

    return f"<!-- component('{key}'): Not found -->"


# Custom Jinja2 global function for executing flows
def flow(path: str, method: str = "GET", **kwargs) -> dict:
    """
    Jinja2 global function to execute another route/flow via internal HTTP call.

    Usage in templates:
        {{ flow('/api/validate', user_id=123).result }}
        {% if flow('/api/check', method='POST', data={'id': 1}).is_valid %}...{% endif %}
        {{ flow('/api/users').result | tojson }}

    Args:
        path: The route path to call (e.g., '/api/users', '/validate/123')
        method: HTTP method (GET, POST, PUT, DELETE). Default: GET
        **kwargs: Additional arguments:
            - body: Request body for POST/PUT (dict or string)
            - query: Query parameters (dict)
            - headers: Additional headers (dict)

    Returns a dict with:
        - result: The response body (parsed as JSON if possible)
        - status: HTTP status code
        - is_valid: True if status < 400
        - error: Error message if failed
    """
    import os
    import json as json_module

    # Get context
    stage = _template_context.get('stage') or os.getenv('STAGE', 'mock')
    project_id = os.getenv('PROJECT_ID')
    router_url = os.getenv('ROUTER_URL', 'http://router:8000')

    if not project_id:
        return {
            'result': None,
            'status': 500,
            'is_valid': False,
            'error': "flow(): PROJECT_ID not set"
        }

    # Build the full URL: router expects /{project_id}/{stage}/{path}
    # Remove leading slash from path if present
    clean_path = path.lstrip('/')
    full_url = f"{router_url}/{project_id}/{stage}/{clean_path}"

    # Prepare request
    body = kwargs.get('body')
    query = kwargs.get('query', {})
    headers = kwargs.get('headers', {})

    # Add query params to URL
    if query:
        from urllib.parse import urlencode
        full_url += '?' + urlencode(query)

    # Make synchronous HTTP request
    try:
        import urllib.request
        import urllib.error

        # Prepare request data
        data = None
        if body is not None:
            if isinstance(body, dict):
                data = json_module.dumps(body).encode('utf-8')
                headers['Content-Type'] = 'application/json'
            else:
                data = str(body).encode('utf-8')

        # Create request
        req = urllib.request.Request(
            full_url,
            data=data,
            headers=headers,
            method=method.upper()
        )

        # Execute request
        with urllib.request.urlopen(req, timeout=30) as response:
            response_body = response.read().decode('utf-8')
            status_code = response.status

            # Try to parse as JSON
            try:
                result = json_module.loads(response_body)
            except json_module.JSONDecodeError:
                result = response_body

            return {
                'result': result,
                'status': status_code,
                'is_valid': status_code < 400,
                'error': None
            }

    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        try:
            error_result = json_module.loads(error_body)
        except json_module.JSONDecodeError:
            error_result = error_body

        return {
            'result': error_result,
            'status': e.code,
            'is_valid': False,
            'error': f"HTTP {e.code}: {e.reason}"
        }

    except urllib.error.URLError as e:
        return {
            'result': None,
            'status': 503,
            'is_valid': False,
            'error': f"Connection error: {str(e.reason)}"
        }

    except Exception as e:
        return {
            'result': None,
            'status': 500,
            'is_valid': False,
            'error': f"flow() error: {str(e)}"
        }


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

# Setup Jinja2 environment with custom loader for project templates
jinja_env = Environment(
    loader=ProjectTemplateLoader(),
    undefined=StrictUndefined
)
jinja_env.filters['tojson'] = json.dumps

# Register global functions
jinja_env.globals['component'] = component
jinja_env.globals['flow'] = flow


def replace_placeholders(data, values: dict = None, state=None, current_node=None, components: dict = None):
    """
    data: string, dict of list met {{ placeholders }}
    values: lokale dict
    state: ExecutionState, met toegang tot andere nodes
    current_node: ExecutableNode, voor backwards traversal als handle niet gevonden
    components: dict van component instances (key -> component met render() method)
    """
    context = dict(values or {})

    # Set template context for global access during template rendering
    set_template_context(state=state, current_node=current_node, components=components)

    try:
        if state:
            # Add only PROCESSED nodes to context
            # Unprocessed nodes with same handle should not override - backwards lookup will find the right one
            for handle, node in state.nodes_by_handle.items():
                if hasattr(node, 'is_processed') and node.is_processed():
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
        # Always clear template context after rendering
        clear_template_context()

def _render_template_string(template_str: str, context: dict) -> str:
    template = jinja_env.from_string(template_str)
    return template.render(context)