from polysynergy_node_runner.execution_context.flow_state import FlowState


class StateLifecycleMixin:
    flow_state: FlowState
    _killed: bool
    _processed: bool
    _exception: Exception | None
    _found_by: list[str]
    _blocking: bool
    _in_loop: bool | None

    def is_killed(self) -> bool:
        return self._killed

    def is_processed(self) -> bool:
        return self._processed

    def get_exception(self):
        return self._exception

    def add_found_by(self, connection_uuid):
        self._found_by.append(connection_uuid)

    def was_found_by(self, connection_uuid):
        return connection_uuid in self._found_by

    def is_blocking(self) -> bool:
        return self._blocking

    def make_blocking(self):
        self._blocking = True

    def unblock(self):
        self._blocking = False

    def is_pending(self):
        return self.flow_state == FlowState.PENDING

    def set_pending(self, pending: bool):
        self.flow_state = FlowState.PENDING

    def set_in_loop(self, loop: None):
        self._in_loop = loop

    def is_in_loop(self):
        return self._in_loop

    def _reset(self):
        self._killed = False
        self._processed = False
        self._found_by = []
        self._exception = None
        return self