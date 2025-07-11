import inspect
import json
import os
import datetime

from polysynergy_nodes.base.execution_context.active_listeners import ActiveListenersService
from polysynergy_nodes.base.execution_context.connection import Connection
from polysynergy_nodes.base.execution_context.execution_state import ExecutionState
from polysynergy_nodes.base.execution_context.execution_storage import DynamoDbExecutionStorageService
from polysynergy_nodes.base.execution_context.flow import Flow
from polysynergy_nodes.base.execution_context.flow_state import FlowState
from polysynergy_nodes.base.execution_context.send_flow_event import send_flow_event
from polysynergy_nodes.base.execution_context.redact_secrets import redact
from polysynergy_nodes.environment.services.env_var_manager import EnvVarManager
from polysynergy_nodes.secret.services.secrets_manager import SecretsManager

# TODO: Refactor - tightly coupled to DynamoDB + execution context, secrets and so on - violates node purity
class ExecutableNode:
    flow_state: FlowState = FlowState.ENABLED
    run_id: str = None

    def __init__(
        self,
        state: ExecutionState,
        flow: Flow,
        id: str,
        handle: str,
        node_setup_version_id: str,
        stateful: bool = True,
        storage: DynamoDbExecutionStorageService = None,
        stage: str = 'mock',
        sub_stage: str = 'mock',
    ):
        self.state: ExecutionState = state
        self.flow: Flow = flow
        self.id: str = id
        self.handle: str = handle
        self.node_setup_version_id: str = node_setup_version_id

        self.factory: callable = None

        # A stateless node is always fully recreated (via its factory) when the flow is resurrected.
        # This ensures the node starts with a clean slate and re-applies its initial values.
        # It's useful for nodes like VariableJson that must re-evaluate dynamic inputs
        # or placeholders on each iteration.

        # Stateless mode is *not* the default because some nodes (like secrets, API calls,
        # or cached computations) are expensive or side-effectful. In those cases, it's more
        # efficient to reuse the same instance and simply reset its flow state.
        self.stateful = stateful

        self.driving_connections = []
        self.in_connections = []
        self.out_connections = []

        self._killed = False
        self._processed = False
        self._blocking = False
        self._found_by = []
        self._exception = None
        self._in_loop: ExecutableNode | None = None
        self._stage = stage
        self._sub_stage = sub_stage

        self.storage = storage

    def set_driving_connections(self, driving_connections: list[Connection]):
        self.driving_connections = driving_connections

    def get_driving_connections(self):
        return self.driving_connections

    def set_in_connections(self, in_connections: list[Connection]):
        self.in_connections = in_connections

    def get_in_connections(self):
        return self.in_connections

    def set_out_connections(self, out_connections: list[Connection]):
        self.out_connections = out_connections

    def is_blocking(self):
        return self._blocking

    def make_blocking(self):
        self._blocking = True

    def unblock(self):
        self._blocking = False

    def is_driven(self):
        return bool(self.driving_connections)

    def has_in_connections(self):
        return bool(self.in_connections)

    def has_out_connections(self):
        return bool(self.out_connections)

    def add_found_by(self, connection_uuid):
        self._found_by.append(connection_uuid)

    def was_found_by(self, connection_uuid):
        return connection_uuid in self._found_by

    def is_pending(self):
        return self.flow_state == FlowState.PENDING

    def set_pending(self, pending: bool):
        self.flow_state = FlowState.PENDING

    def set_in_loop(self, loop: None):
        self._in_loop = loop

    def is_in_loop(self):
        return self._in_loop

    def _kill_forward(self, connection, execution_flow: dict[str, any]):
        target_node = self.flow.nodes[connection.target_node_id]
        if not target_node.is_killed() and self.flow.should_kill_node(target_node):
            target_node.kill(execution_flow)

    def snipe(self, execution_flow: dict[str, any]):
        self._killed = True
        print('Sniped:', self.handle, self.id, self.__class__.__name__)

        for node_order in execution_flow['nodes_order']:
            if node_order['id'] == self.id:
                node_order['killed'] = True

        for connection in self.out_connections + self.in_connections + self.driving_connections:
            connection.make_killer()

    def kill(self, execution_flow: dict[str, any]):
        self._killed = True

        print('Killed:', self.handle, self.id, self.__class__.__name__)

        for node_order in execution_flow['nodes_order']:
            if node_order['id'] == self.id:
                node_order['killed'] = True
        for connection in self.out_connections:
            connection.make_killer()
            self._kill_forward(connection, execution_flow)

        return self

    def _find_nodes_until(self, match_end_node_fn, skip_node_fn=None, post_process_fn=None):
        visited = set()
        collected_nodes = []
        end_node = None

        def traverse(node):
            nonlocal end_node
            if node.id in visited:
                return
            visited.add(node.id)

            for connection in node.out_connections:
                target_node = self.state.get_node_by_id(connection.target_node_id)
                if target_node is None:
                    continue

                if match_end_node_fn(target_node):
                    end_node = target_node
                    continue

                if skip_node_fn and skip_node_fn(target_node):
                    continue

                if post_process_fn:
                    post_process_fn(target_node)

                collected_nodes.append(target_node)
                traverse(target_node)

        traverse(self)
        return collected_nodes, end_node

    def find_nodes_for_jump(self):
        return self._find_nodes_until(
            match_end_node_fn=lambda node: node.__class__.__name__ == "Jump"
        )

    def find_nodes_in_loop(self):
        return self._find_nodes_until(
            match_end_node_fn=lambda node: node.__class__.__name__.startswith("LoopEnd"),
            skip_node_fn=lambda node: node.__class__.__name__.startswith("ListLoop"),
            post_process_fn=lambda node: node.set_in_loop(self)
        )

    def _reset(self):
        self._killed = False
        self._processed = False
        self._found_by = []
        self._exception = None

        for connection in self.in_connections + self.out_connections:
            connection.resurrect()

        return self

    def resurrect(self):
        if self.stateful:
            return self._reset()

        new_node = self.factory()
        self.flow.register_node(new_node)
        for connection in self.in_connections + self.out_connections:
            connection.resurrect()
        return new_node

    def is_killed(self):
        return self._killed

    def is_processed(self):
        return self._processed

    def apply_from_driving_connection(self, connection):
        if self.flow_state == FlowState.ENABLED:
            self.apply_from_incoming_connection(connection)
            return

        # Flow in means, try to apply the variables from the source
        # if they are the same, it will do so
        if self.flow_state != FlowState.FLOW_IN:
            return

        source_node = self.flow.get_node(connection.source_node_id)
        source_attributes = list(getattr(type(source_node), '__annotations__', {}).keys())
        source_attributes = [a for a in source_attributes if not a.startswith("_")]

        for attr in source_attributes:
            if hasattr(self, attr):
                setattr(self, attr, getattr(source_node, attr))

    def apply_from_incoming_connection(self, connection):
        var = self.state.get_connection_source_variable(connection)
        self._apply_attribute(connection.target_handle, var)

    def _apply_attribute(self, property_name, value):
        if "." in property_name:
            parent_attr, sub_key = property_name.split(".", 1)
            parent_dict = getattr(self, parent_attr, {})

            if not isinstance(parent_dict, dict):
                raise TypeError(
                    f"Can't configure: '{parent_attr}' existing type is: {type(parent_dict).__name__}, not a dict!")

            parent_dict[sub_key] = value
            setattr(self, parent_attr, parent_dict)
        else:
            setattr(self, property_name, value)

    def execute(self):
        raise NotImplementedError()

    def to_dict(self):
        vars_dict = {}

        for a in type(self).__annotations__:
            if not a.startswith("_"):
                raw_value = getattr(self, a, None)
                vars_dict[a] = self.flow.make_json_serializable(raw_value)
        return vars_dict

    def _apply_placeholder_replacements(self):
        from polysynergy_nodes.base.execution_context.replace_placeholders import replace_placeholders

        for attr_name in getattr(type(self), '__annotations__', {}):
            if attr_name.startswith("_"):
                continue

            val = getattr(self, attr_name, None)
            if isinstance(val, (str, dict, list)):
                replaced = replace_placeholders(data=val, values=self.__dict__, state=self.state)
                setattr(self, attr_name, replaced)

    async def state_execute(self, execution_flow: dict[str, any]):
        has_listener = ActiveListenersService().has_listener(
            self.node_setup_version_id
        )

        self._processed = True
        order = len(execution_flow['nodes_order'])

        if has_listener:
            send_flow_event(
                flow_id=self.node_setup_version_id,
                run_id=self.run_id,
                node_id=self.id,
                event_type='start_node',
                order=order,
            )

        execution_flow['nodes_order'].append({
            "id": self.id,
            "handle": self.handle,
            "type": self.__class__.__name__,
            "order": order,
        })
        try:
            self.resolve_secret()
            self.resolve_environment_variable()
            if inspect.iscoroutinefunction(type(self).execute):
                await self.execute()
            else:
                self.execute()

            # self.execute()
        except NotImplementedError as e:
            print(f"Node {self.handle} does not implement execute method")
            self._exception = e
        except Exception as e:
            print(f"Unhandled exception in node {self.handle}: {e}")
            self._exception = e

        result_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "variables": redact(
                truncate_large_values(self.to_dict()),
                {
                    secret.get("value"): secret
                    for secret in getattr(self.flow, "secrets_map", {}).values()
                    if secret.get("value")
                }
            ),
            "error_type": type(self._exception).__name__ if self._exception else None,
            "error": str(self._exception) if self._exception else None,
            "killed": self.is_killed(),
            "processed": self.is_processed(),
        }

        self.storage.store_node_result(
            flow_id=self.node_setup_version_id,
            run_id=self.run_id,
            node_id=self.id,
            order=order,
            result=json.dumps(result_data, default=str),
            stage= self._stage,
            sub_stage=self._sub_stage
        )

        if hasattr(self, 'true_path') and not self.true_path:
            for connection in self.flow.get_out_connections_on_true_path(self.id):
                connection.make_killer()

        if hasattr(self, 'false_path') and not self.false_path:
            for connection in self.flow.get_out_connections_on_false_path(self.id):
                connection.make_killer()

        if hasattr(self, 'false_path') and self.false_path:
            for connection in self.flow.get_out_connections_except_on_false_path(self.id):
                connection.make_killer()

        if has_listener:
            print(f"Sending flow event for node {self.handle} with status")
            send_flow_event(
                flow_id=self.node_setup_version_id,
                run_id=self.run_id,
                node_id=self.id,
                event_type='end_node',
                order=order,
                status=self.is_killed() and 'killed' or 'success',
            )

    def resolve_environment_variable(self):
        if not self.__class__.__name__.startswith("VariableEnvironment"):
            return

        variable_key = getattr(self, "true_path", None)
        if not variable_key:
            return

        project_id = os.getenv("PROJECT_ID", None)
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")

        effective_stage = (
            self._sub_stage if self._stage == "mock" and self._sub_stage != "mock" else self._stage
        )

        value = EnvVarManager().get_var(project_id, effective_stage, variable_key)

        if not value:
            return '<ENV_VAR::NOT::FOUND>'

        setattr(self, "true_path", value)


    def resolve_secret(self):
        if not self.__class__.__name__.startswith("VariableSecret"):
            return

        secret_key = getattr(self, "true_path", None)
        if not secret_key:
            return

        project_id = os.getenv("PROJECT_ID", None)
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")

        effective_stage = (
            self._sub_stage if self._stage == "mock" and self._sub_stage != "mock" else self._stage
        )

        secret = SecretsManager().get_secret_by_key(secret_key, project_id, effective_stage)

        if not secret or not secret.get("value"):
            return '<SECRET::NOT::FOUND>'

        self.flow.secrets_map[secret_key] = secret
        setattr(self, "true_path", secret.get("value"))


MAX_PREVIEW_SIZE = 16384

def truncate_large_values(obj):
    if isinstance(obj, dict):
        return {k: truncate_large_values(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [truncate_large_values(v) for v in obj]
    elif isinstance(obj, (str, bytes)) and len(obj) > MAX_PREVIEW_SIZE:
        return f"<truncated {len(obj)} bytes>"
    return obj