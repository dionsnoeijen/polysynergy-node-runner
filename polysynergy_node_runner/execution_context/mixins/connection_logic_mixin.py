from polysynergy_node_runner.execution_context.connection import Connection


class ConnectionLogicMixin:
    _driving_connections: list[Connection] = []
    _in_connections: list[Connection] = []
    _out_connections: list[Connection] = []

    def set_driving_connections(self, driving_connections: list[Connection]):
        self._driving_connections = driving_connections

    def get_driving_connections(self):
        return self._driving_connections

    def set_in_connections(self, in_connections: list[Connection]):
        self._in_connections = in_connections

    def get_in_connections(self) -> list:
        return self._in_connections

    def get_alive_in_connections(self) -> list:
        return [c for c in self._in_connections if not c.is_killer()]

    def get_out_connections_except_on_false_path(self) -> list:
        return [c for c in self._out_connections if c.source_handle != "false_path"]

    def get_out_connections_on_true_path(self) -> list:
        return [c for c in self._out_connections if c.source_handle == "true_path"]

    def get_out_connections_on_false_path(self) -> list:
        return [c for c in self._out_connections if c.source_handle == "false_path"]

    def set_out_connections(self, out_connections: list[Connection]):
        self._out_connections = out_connections

    def get_out_connections(self) -> list:
        return self._out_connections

    def is_driven(self) -> bool:
        return bool(self._driving_connections)

    def has_in_connections(self) -> bool:
        return bool(self._in_connections)

    def has_out_connections(self) -> bool:
        return bool(self._out_connections)
