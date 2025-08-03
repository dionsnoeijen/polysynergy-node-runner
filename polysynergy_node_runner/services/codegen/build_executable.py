import copy

from polysynergy_node_runner.services.codegen.steps.build_connections_code import build_connections_code
from polysynergy_node_runner.services.codegen.steps.build_group_nodes_code import build_group_nodes_code
from polysynergy_node_runner.services.codegen.steps.build_nodes_code import build_nodes_code
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
        if nd.get("type") in ["group"]:
            continue
        path = nd["path"]
        code = nd.get("code", "")
        version = nd.get("version", 0.0)
        version_key = f"{path}-v{str(version).replace('.', '_')}"
        if code.strip() and version_key not in path_version_map:
            cleaned = unify_node_code(code, collected_imports, version)
            path_version_map[version_key] = cleaned

    code_parts = [HEADER]

    code_parts.append(f"NODE_SETUP_VERSION_ID = \"{str(id)}\"")

    if collected_imports:
        code_parts.append("\n".join(sorted(collected_imports)))

    for _, ctext in path_version_map.items():
        if ctext.strip():
            code_parts.append(ctext)

    code_parts.append(build_group_nodes_code(conns_data, groups_with_output))

    rewrite_connections_for_groups(conns_data)

    code_parts.append("""\ndef create_execution_environment(mock = False, run_id:str = \"\", stage:str=None, sub_stage:str=None):
        storage.clear_previous_execution(NODE_SETUP_VERSION_ID)

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
            execution_flow=execution_flow
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

    flow, execution_flow, state = create_execution_environment(True, run_id=run_id, stage="mock", sub_stage=sub_stage)

    node_id = str(node_id)
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

    if event:
        for node in entry_nodes:
            if node.path == 'polysynergy_nodes.route.route.Route':
                node.method = event.get("httpMethod", "GET")
                node.headers = event.get("headers", {})
                node.body = event.get("body", "")
                node.query = event.get("queryStringParameters", {})
                node.cookies = event.get("cookies", {})
                node.route_variables = event.get("pathParameters", {})

    await flow.execute_node(entry_nodes[0])

    storage.store_connections_result(
        flow_id=NODE_SETUP_VERSION_ID,
        run_id=run_id,
        connections=[c.to_dict() for c in state.connections],
    )

    return execution_flow, flow, state""")

    code_parts.append("""\nimport json

def lambda_handler(event, context):
    stage = event.get("stage", "mock")
    sub_stage = event.get("sub_stage", "mock")
    node_id = event.get("node_id")

    run_id = str(uuid.uuid4())


    try:
        # Is this a mock run triggered from the user interface?
        # in that case, it should start with the node_id that is provided.
        is_ui_mock = stage == "mock" and node_id is not None
        if is_ui_mock:
            print("Running in mock mode with node_id:", node_id)
            has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID)
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
                has_listener = active_listeners_service.has_listener(NODE_SETUP_VERSION_ID)

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
                    execution_flow, flow, state = future.result()
            except RuntimeError:
                # No running loop, we can use asyncio.run
                execution_flow, flow, state = asyncio.run(execute_with_production_start(event, run_id, stage))
            print('request_id: ', context.aws_request_id)

            for node in execution_flow.get("nodes_order", []):
                print("NODE TYPE:", node.get("type"), "| PATH:", node.get("path", ''))

            last_http_response = next(
                (node for node in reversed(execution_flow.get("nodes_order", [])) 
                 if node.get("type", "").startswith("HttpResponse")),
                None
            )

            if last_http_response:
                variables = last_http_response.get("variables", {})
                http_response_node = state.get_node_by_id(last_http_response.get("id", ""))
                response = {
                    "statusCode": http_response_node.response.get('status', 100),
                    "headers": http_response_node.response.get('headers', {}),
                    "body": http_response_node.response.get('body', '')
                }

                print("FINAL RESPONSE", last_http_response, variables, response)

                if is_test_run and has_listener:
                    send_flow_event(
                        NODE_SETUP_VERSION_ID,
                        run_id,
                        None,
                        'run_end'
                    )

                return response

            if is_test_run and has_listener:
                send_flow_event(
                    NODE_SETUP_VERSION_ID,
                    run_id,
                    None,
                    'run_end'
                )

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
