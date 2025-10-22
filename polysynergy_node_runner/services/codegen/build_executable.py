import copy

from polysynergy_node_runner.services.codegen.steps.build_connections_code import build_connections_code
from polysynergy_node_runner.services.codegen.steps.build_group_nodes_code import build_group_nodes_code
from polysynergy_node_runner.services.codegen.steps.build_nodes_code import build_nodes_code, discover_node_code
from polysynergy_node_runner.services.codegen.steps.find_groups_with_output import find_groups_with_output
from polysynergy_node_runner.services.codegen.steps.rewrite_connections_for_groups import rewrite_connections_for_groups
from polysynergy_node_runner.services.codegen.steps.unify_node_code import unify_node_code

HEADER = """#!/usr/bin/env python3

import types
import logging
import uuid
import asyncio
from typing import get_origin, get_args

from polysynergy_node_runner.execution_context.connection import Connection
from polysynergy_node_runner.execution_context.connection_context import ConnectionContext
from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.executable_node import ExecutableNode
from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.execution_context.flow_state import FlowState
from polysynergy_node_runner.execution_context.utils.connections import get_driving_connections, get_in_connections, \
    get_out_connections
from polysynergy_node_runner.services.active_listeners_service import get_active_listeners_service, \
    ActiveListenersService
from polysynergy_node_runner.services.env_var_manager import get_env_var_manager
from polysynergy_node_runner.services.execution_storage_service import DynamoDbExecutionStorageService, get_execution_storage_service
from polysynergy_node_runner.execution_context.send_flow_event import send_flow_event
from polysynergy_node_runner.services.secrets_manager import get_secrets_manager

logger = logging.getLogger()
logger.setLevel(logging.INFO)

storage: DynamoDbExecutionStorageService = get_execution_storage_service()
active_listeners_service: ActiveListenersService = get_active_listeners_service()
"""

CONNECTIONS = """
connections = []
"""

INITIALIZERS = """
execution_flow = {"nodes_order": [], "connections": []}
state = ExecutionState()
flow = Flow(connections, state, execution_flow)
"""


def generate_code_from_json(json_data, id):
    json_data = copy.deepcopy(json_data)
    nodes_data = json_data.get("nodes", [])
    conns_data = json_data.get("connections", [])

    groups_with_output = find_groups_with_output(conns_data)

    collected_imports = set()
    path_version_map = {}

    for nd in nodes_data:
        if nd.get("type") in ["group", "warp_gate"]:
            continue
        path = nd["path"]
        version = nd.get("version", 0.0)
        version_key = f"{path}-v{str(version).replace('.', '_')}"
        
        # Always discover code from path, ignore the code field entirely
        code = discover_node_code(nd)
        
        if code.strip() and version_key not in path_version_map:
            cleaned = unify_node_code(code, collected_imports, version)
            path_version_map[version_key] = cleaned

    # Separate __future__ imports from other imports
    future_imports = {imp for imp in collected_imports if imp.startswith("from __future__")}
    other_imports = collected_imports - future_imports
    
    code_parts = []
    
    # Add shebang first (if no __future__ imports) or __future__ imports first
    if future_imports:
        code_parts.append("#!/usr/bin/env python3")
        code_parts.append("\n".join(sorted(future_imports)))
        # Add rest of header without shebang
        code_parts.append(HEADER.replace("#!/usr/bin/env python3\n\n", ""))
    else:
        # Add the full header with shebang
        code_parts.append(HEADER)

    code_parts.append(f"NODE_SETUP_VERSION_ID = \"{str(id)}\"")

    # Add remaining imports
    if other_imports:
        code_parts.append("\n".join(sorted(other_imports)))

    for _, ctext in path_version_map.items():
        if ctext.strip():
            code_parts.append(ctext)

    code_parts.append(build_group_nodes_code(conns_data, groups_with_output))

    rewrite_connections_for_groups(conns_data)

    code_parts.append("""\ndef create_execution_environment(mock = False, run_id:str = \"\", stage:str=None, sub_stage:str=None, trigger_node_id:str=None):
        storage.clear_previous_execution(NODE_SETUP_VERSION_ID, current_run_id=run_id)

        execution_flow = { "run_id": run_id, "nodes_order": [], "connections": [], "execution_data": []}

        state = ExecutionState()
        flow = Flow()

        node_context = Context(
            run_id=run_id,
            node_setup_version_id=NODE_SETUP_VERSION_ID,
            state=state,
            flow=flow,
            storage=storage,
            active_listeners=active_listeners_service,
            secrets_manager=get_secrets_manager(),
            env_var_manager=get_env_var_manager(),
            stage=stage if stage else "mock",
            sub_stage=sub_stage if sub_stage else "mock",
            execution_flow=execution_flow,
            trigger_node_id=trigger_node_id
        )

        connection_context = ConnectionContext(
            state=state
        )

        connections = []
        """)
    code_parts.append(build_connections_code(conns_data, nodes_data, groups_with_output))
    code_parts.append("        state.connections = connections")
    code_parts.append(build_nodes_code(nodes_data, groups_with_output))
    code_parts.append("        return flow, execution_flow, state")
    code_parts.append("""\nasync def execute_with_mock_start_node(node_id:str, run_id:str, sub_stage:str):

    node_id = str(node_id)

    flow, execution_flow, state = create_execution_environment(
        True,
        run_id=run_id,
        stage="mock",
        sub_stage=sub_stage,
        trigger_node_id=node_id
    )

    
    node = state.get_node_by_id(str(node_id))
    if node is None:
        raise ValueError(f"Node ID {node_id} not found.")

    await flow.execute_node(node)
    storage.store_connections_result(
        flow_id=NODE_SETUP_VERSION_ID,
        run_id=run_id,
        connections=[c.to_dict() for c in state.connections],
    )

    return execution_flow


async def execute_with_production_start(event=None, run_id:str=None, stage:str=None):
    flow, execution_flow, state = create_execution_environment(run_id=run_id, stage=stage)

    entry_nodes = [n for n in state.nodes if n.path in ['polysynergy_nodes.route.route.Route', 'polysynergy_nodes.schedule.schedule.Schedule']]

    if not entry_nodes:
        raise ValueError("No valid entry node found (expected 'route' or 'schedule').")

    # Capture the entry node type for later use
    entry_node = entry_nodes[0]
    is_schedule = entry_node.path == 'polysynergy_nodes.schedule.schedule.Schedule'

    if event:
        for node in entry_nodes:
            if node.path == 'polysynergy_nodes.route.route.Route':
                node.method = event.get("httpMethod", "GET")
                node.headers = event.get("headers", {})
                node.body = event.get("body", "")
                node.query = event.get("queryStringParameters", {})
                node.cookies = event.get("cookies", {})
                node.route_variables = event.get("pathParameters", {})

    await flow.execute_node(entry_node)

    storage.store_connections_result(
        flow_id=NODE_SETUP_VERSION_ID,
        run_id=run_id,
        connections=[c.to_dict() for c in state.connections],
    )

    return execution_flow, flow, state, is_schedule""")

    code_parts.append("""\n
async def execute_with_resume(run_id: str, resume_node_id: str, user_input):
    \"\"\"
    Resume a paused flow from a Human-in-the-Loop node.

    Args:
        run_id: The existing run_id to resume (must match paused execution)
        resume_node_id: The node ID to resume from (typically the HIL node)
        user_input: User response data - dict for structured input, bool for confirmation

    Returns:
        execution_flow dict with execution results
    \"\"\"
    print(f"[RESUME] Starting resume for run_id={run_id}, node={resume_node_id}")

    # Check if there's a listener and send resume_start event
    has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID)
    if has_listener:
        send_flow_event(
            NODE_SETUP_VERSION_ID,
            run_id,
            None,
            'resume_start'
        )
        print(f"[RESUME] Sent resume_start event")

    # Get all previous node states from DynamoDB
    nodes_state = storage.get_all_nodes_for_run(NODE_SETUP_VERSION_ID, run_id)
    print(f"[RESUME] Found {len(nodes_state)} nodes with saved state")

    if not nodes_state:
        raise ValueError(f"No saved state found for run_id {run_id}")

    # Check if this flow was already resumed by checking if resume node already has user_response
    resume_node_state = next((ns for ns in nodes_state if ns['node_id'] == resume_node_id), None)
    if resume_node_state:
        existing_user_response = resume_node_state['data'].get('variables', {}).get('user_response')
        if existing_user_response:
            print(f"[RESUME] Flow already resumed - user_response already set to: {existing_user_response}")
            raise ValueError(f"Flow {run_id} was already resumed. Cannot resume twice.")

    # Get stage/sub_stage from first node to preserve execution context
    first_node_data = nodes_state[0]['data'] if nodes_state else {}
    original_stage = "mock"  # Default
    original_sub_stage = "mock"  # Default

    # Try to extract from execution metadata if available
    # (We'll improve this later if stage/sub_stage needs to be stored explicitly)

    # Create execution environment WITHOUT clearing previous execution
    # We need the old state to reconstruct!
    flow, execution_flow, state = create_execution_environment(
        run_id=run_id,
        stage=original_stage,
        sub_stage=original_sub_stage,
        trigger_node_id=resume_node_id
    )

    print(f"[RESUME] Created execution environment with {len(state.nodes)} fresh nodes")

    # Reconstruct the execution_flow.nodes_order from previous execution
    # This ensures the UI shows the complete execution history
    # Note: We exclude the resume node itself as it will be re-executed and added again
    for node_state in nodes_state:
        # Skip the resume node - it will be executed again with updated user_input
        if node_state['node_id'] == resume_node_id:
            continue

        node_data = node_state['data']
        execution_flow['nodes_order'].append({
            'id': node_state['node_id'],
            'handle': node_data.get('handle', ''),
            'type': node_data.get('type', ''),
            'order': node_state['order'],
            'variables': node_data.get('variables', {}),
            'error': node_data.get('error'),
            'error_type': node_data.get('error_type'),
            'killed': node_data.get('killed', False),
            'processed': node_data.get('processed', False)
        })

    # Find the highest order number to continue from
    max_order = max((ns['order'] for ns in nodes_state), default=-1)
    print(f"[RESUME] Reconstructed {len(execution_flow['nodes_order'])} nodes in execution_flow, max_order={max_order}")

    # Map all saved state back onto the nodes
    for node_state in nodes_state:
        node_id = node_state['node_id']
        node = state.get_node_by_id(node_id)

        if not node:
            print(f"[RESUME] Warning: Node {node_id} not found in state, skipping")
            continue

        # Restore all variables from saved state
        variables = node_state['data'].get('variables', {})
        for var_name, var_value in variables.items():
            if hasattr(node, var_name):
                try:
                    setattr(node, var_name, var_value)
                except Exception as e:
                    print(f"[RESUME] Warning: Could not set {var_name} on {node_id}: {e}")

        # Mark node as processed if it was completed
        if node_state['data'].get('processed'):
            node._processed = True
            print(f"[RESUME] Marked {node.handle} as processed")

    # Apply user input to the resume node
    resume_node = state.get_node_by_id(resume_node_id)
    if not resume_node:
        raise ValueError(f"Resume node {resume_node_id} not found")

    print(f"[RESUME] Applying user input to {resume_node.handle}: {user_input}")

    # Handle both dict and bool user_input
    if isinstance(user_input, dict):
        # Dict: loop through and set each key/value
        for key, value in user_input.items():
            if hasattr(resume_node, key):
                setattr(resume_node, key, value)
    elif isinstance(user_input, bool):
        # Boolean: set user_input_data directly (for AgnoAgent HITL confirmation)
        if hasattr(resume_node, 'user_input_data'):
            setattr(resume_node, 'user_input_data', user_input)
            print(f"[RESUME] Set user_input_data={user_input} for HITL confirmation")
    else:
        # Fallback: try to set as user_response for old HITL nodes
        if hasattr(resume_node, 'user_response'):
            setattr(resume_node, 'user_response', str(user_input))

    # IMPORTANT: Mark resume node as NOT processed so it executes again
    resume_node._processed = False

    # Restore connection state
    stored_connections = storage.get_connections_result(NODE_SETUP_VERSION_ID, run_id)
    if stored_connections:
        print(f"[RESUME] Restoring {len(stored_connections)} connection states")
        for conn_data in stored_connections:
            # Find connection by UUID
            conn = next((c for c in state.connections if c.uuid == conn_data.get('uuid')), None)
            if conn and conn_data.get('is_killer'):
                conn.make_killer()

    print(f"[RESUME] Starting execution from {resume_node.handle}")

    # Execute from the resume node
    await flow.execute_node(resume_node)

    # Store updated connections
    storage.store_connections_result(
        flow_id=NODE_SETUP_VERSION_ID,
        run_id=run_id,
        connections=[c.to_dict() for c in state.connections],
    )

    print(f"[RESUME] Resume complete, executed {len(execution_flow.get('nodes_order', []))} new nodes")

    # Send resume_end event
    if has_listener:
        send_flow_event(
            NODE_SETUP_VERSION_ID,
            run_id,
            None,
            'resume_end'
        )
        print(f"[RESUME] Sent resume_end event")

    return execution_flow
""")

    code_parts.append("""\nimport json

def lambda_handler(event, context):
    stage = event.get("stage", "mock")
    sub_stage = event.get("sub_stage", "mock")
    node_id = event.get("node_id")

    # Use provided run_id from API if available, otherwise generate new one
    run_id = event.get("run_id")
    if not run_id:
        run_id = str(uuid.uuid4())


    try:
        # Check if this is a resume request for Human-in-the-Loop
        is_resume = event.get("resume", False)
        if is_resume:
            resume_node_id = event.get("resume_node_id")
            user_input = event.get("user_input", {})

            if not resume_node_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "resume_node_id is required for resume requests"})
                }

            if not run_id:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"error": "run_id is required for resume requests"})
                }

            print(f"[HIL] Resuming flow: run_id={run_id}, node={resume_node_id}")

            # Execute the resume
            execution_flow = asyncio.run(execute_with_resume(run_id, resume_node_id, user_input))

            print(f"[HIL] Resume completed successfully")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Flow resumed successfully",
                    "run_id": run_id,
                    "execution_flow": execution_flow
                })
            }

        # Is this a mock run triggered from the user interface?
        # in that case, it should start with the node_id that is provided.
        is_ui_mock = stage == "mock" and node_id is not None
        if is_ui_mock:
            print("Running in mock mode with node_id:", node_id)
            has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID, first_run=True)
            print("Has listener:", has_listener, NODE_SETUP_VERSION_ID)
            if has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_start'
                )
            execution_flow = asyncio.run(execute_with_mock_start_node(node_id, run_id, sub_stage))
            if has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_end'
                )
            return {
                "statusCode": 200,
                "body": json.dumps(execution_flow)
            }
        else:
            # This is a production run triggered from the Router.
            # then this could still be a mock run. Imagine testing it with some
            # front-end or other application. We need to check the lambda name itself
            # to determine if that is true. We do want do run a production_start
            # because the flow will take the actual arguments from the application you
            # are testing with...
            is_test_run = False
            if context.function_name.endswith("_mock"):
                is_test_run = True

            has_listener = False
            if is_test_run:
                has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID, first_run=True)

                if has_listener:
                    send_flow_event(
                        NODE_SETUP_VERSION_ID,
                        run_id,
                        None,
                        'run_start'
                    )


            # Handle async execution properly for production
            try:
                # Check if we're already in an event loop
                asyncio.get_running_loop()
                # If we get here, we're in a running loop, run in a separate thread
                import concurrent.futures

                def run_production_async():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(execute_with_production_start(event, run_id, stage))
                    finally:
                        loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_production_async)
                    execution_flow, flow, state, is_schedule = future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run
                execution_flow, flow, state, is_schedule = asyncio.run(execute_with_production_start(event, run_id, stage))
            print('request_id: ', context.aws_request_id)

            last_http_response = next(
                (node for node in reversed(execution_flow.get("nodes_order", [])) 
                 if node.get("type", "").startswith("HttpResponse")),
                None
            )

            if last_http_response:
                variables = last_http_response.get("variables", {})
                http_response_node = state.get_node_by_id(last_http_response.get("id", ""))

                print("DEBUG: http_response_node:", http_response_node)
                print("DEBUG: http_response_node.response:", http_response_node.response)
                print("DEBUG: type(http_response_node.response):", type(http_response_node.response))
                
                # More defensive response construction
                node_response = http_response_node.response
                print("DEBUG: node_response assigned:", node_response, "type:", type(node_response))
                
                if isinstance(node_response, dict):
                    # Handle both 'status' and 'statusCode' keys for compatibility
                    status_part = node_response.get('status', node_response.get('statusCode', 200))
                    headers_part = node_response.get('headers', {})
                    body_part = node_response.get('body', '')
                else:
                    print("ERROR: node_response is not a dict, using fallback values")
                    status_part = 200
                    headers_part = {"Content-Type": "application/json"}
                    body_part = str(node_response) if node_response is not None else ""
                
                print("DEBUG: status_part:", status_part, "type:", type(status_part))
                print("DEBUG: headers_part:", headers_part, "type:", type(headers_part))
                print("DEBUG: body_part:", body_part, "type:", type(body_part))
                
                final_lambda_response = {
                    "statusCode": status_part,
                    "headers": headers_part,
                    "body": body_part
                }
                
                print("DEBUG: constructed final_lambda_response:", final_lambda_response)
                print("DEBUG: type(final_lambda_response):", type(final_lambda_response))
                print("FINAL RESPONSE", last_http_response, variables, final_lambda_response)

                if is_test_run and has_listener:
                    send_flow_event(
                        NODE_SETUP_VERSION_ID,
                        run_id,
                        None,
                        'run_end'
                    )

                print("DEBUG: About to return final_lambda_response:", final_lambda_response, "type:", type(final_lambda_response))
                
                # Safety check to ensure we always return a proper dict
                if not isinstance(final_lambda_response, dict):
                    print("SAFETY: final_lambda_response is not a dict, creating fallback response")
                    final_lambda_response = {
                        "statusCode": 500,
                        "headers": {"Content-Type": "application/json"},
                        "body": json.dumps({"error": "Invalid response format", "original_response": str(final_lambda_response)})
                    }
                
                # Ensure required keys exist
                if "statusCode" not in final_lambda_response:
                    final_lambda_response["statusCode"] = 200
                if "headers" not in final_lambda_response:
                    final_lambda_response["headers"] = {}
                if "body" not in final_lambda_response:
                    final_lambda_response["body"] = ""
                    
                print("DEBUG: FINAL SAFETY CHECK - returning:", final_lambda_response, "type:", type(final_lambda_response))
                
                # Absolutely explicit return to avoid any scoping issues
                lambda_response_to_return = dict(final_lambda_response)  # Create a copy
                print("DEBUG: EXPLICITLY RETURNING:", lambda_response_to_return)
                return lambda_response_to_return

            if is_test_run and has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_end'
                )

            # Handle missing HttpResponse based on execution type
            if is_schedule:
                # Schedules don't need HttpResponse nodes - return success
                logger.info("Schedule execution completed successfully - no HttpResponse node required")
                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "message": "Schedule executed successfully",
                        "request_id": context.aws_request_id,
                        "execution_type": "schedule"
                    })
                }
            else:
                # Routes require HttpResponse nodes
                logger.error("Error: No valid HttpResponse node found. Make sure the flow leads to a response. 500 Response given.")
                return {
                    "statusCode": 500,
                    "body": json.dumps({
                        "error": "No valid HttpResponse node found. Make sure the flow leads to a response.",
                        "request_id": context.aws_request_id
                    })
                }

    except ValueError as e:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": str(e)})
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
""")

    return "\n\n".join(code_parts)
