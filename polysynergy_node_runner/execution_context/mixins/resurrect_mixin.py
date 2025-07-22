from polysynergy_node_runner.execution_context.context import Context


class ResurrectMixin:
    context: Context
    _in_connections: list = []
    _out_connections: list = []
    stateful: bool
    factory: callable = None

    def _reset(self):
        self._killed = False
        self._processed = False
        self._found_by = []
        self._exception = None

        for connection in self._in_connections + self._out_connections:
            connection.resurrect()

        return self

    def resurrect(self):
        if self.stateful:
            return self._reset()

        new_node = self.factory()
        self.context.state.register_node(new_node)
        for connection in self._in_connections + self._out_connections:
            connection.resurrect()
        return new_node