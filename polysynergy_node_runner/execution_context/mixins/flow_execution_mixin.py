import inspect
from typing import Optional, TYPE_CHECKING

from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.send_flow_event import send_flow_event
if TYPE_CHECKING:
    from polysynergy_node_runner.execution_context.executable_node import ExecutableNode

class FlowExecutionMixin:

    context: Context
    id: str = None
    handle: str = None
    run_id: str = None
    _killed: bool = False
    _processed: bool = False
    _exception: Exception = None
    _blocking: bool = False
    _in_loop: Optional["ExecutableNode"] | None = None
    _found_by: list[str] = []
    _out_connections: list = []
    _in_connections: list = []
    _driving_connections: list = []

    _resolve_secret: callable
    _resolve_environment_variable: callable
    get_out_connections_on_true_path: callable
    get_out_connections_on_false_path: callable
    get_out_connections_except_on_false_path: callable

    def _kill_forward(self, connection):
        target_node = self.context.state.get_node_by_id(connection.target_node_id)
        if not target_node.is_killed() and self.context.flow.should_kill_node(target_node):
            target_node.kill()

    def is_processed(self):
        return self._processed

    def snipe(self, execution_flow: dict[str, any]):
        self._killed = True
        print('Sniped:', self.handle, self.id, self.__class__.__name__)

        for node_order in execution_flow['nodes_order']:
            if node_order['id'] == self.id:
                node_order['killed'] = True

        for connection in self._out_connections + self._in_connections + self._driving_connections:
            connection.make_killer()

    def kill(self):
        self._killed = True
        print('Killed:', self.handle, self.id, self.__class__.__name__)

        for node_order in self.context.execution_flow['nodes_order']:
            if node_order['id'] == self.id:
                node_order['killed'] = True
        for connection in self._out_connections:
            connection.make_killer()
            self._kill_forward(connection)

        return self

    def is_killed(self):
        return self._killed

    def execute(self):
        raise NotImplementedError()

    async def state_execute(self):
        has_listener = self.context.active_listeners.has_listener(
            self.context.node_setup_version_id
        )

        self._processed = True
        order = len(self.context.execution_flow['nodes_order'])

        if has_listener:
            send_flow_event(
                flow_id=self.context.node_setup_version_id,
                run_id=self.context.run_id,
                node_id=self.id,
                event_type='start_node',
                order=order,
            )

        self.context.execution_flow['nodes_order'].append({ "id": self.id, "handle": self.handle, "type": self.__class__.__name__, "order": order})

        try:
            self._resolve_secret()
            self._resolve_environment_variable()
            if inspect.iscoroutinefunction(type(self).execute):
                await self.execute()
            else:
                self.execute()

        except NotImplementedError as e:
            print(f"Node {self.handle} does not implement execute method")
            self._exception = e
        except Exception as e:
            print(f"Unhandled exception in node {self.handle}: {e}")
            self._exception = e

        self.context.storage.store_node_result(
            node=self,
            flow_id=self.context.node_setup_version_id,
            run_id=self.context.run_id,
            order=order,
            stage= self.context.stage,
            sub_stage=self.context.sub_stage
        )

        if hasattr(self, 'true_path') and not self.true_path:
            for connection in self.get_out_connections_on_true_path():
                connection.make_killer()

        if hasattr(self, 'false_path') and not self.false_path:
            for connection in self.get_out_connections_on_false_path():
                connection.make_killer()

        if hasattr(self, 'false_path') and self.false_path:
            for connection in self.get_out_connections_except_on_false_path():
                connection.make_killer()

        if has_listener:
            print(f"Sending flow event for node {self.handle} with status")
            send_flow_event(
                flow_id=self.context.node_setup_version_id,
                run_id=self.context.run_id,
                node_id=self.id,
                event_type='end_node',
                order=order,
                status=self.is_killed() and 'killed' or 'success',
            )