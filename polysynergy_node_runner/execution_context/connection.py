from polysynergy_node_runner.execution_context.connection_context import ConnectionContext


class Connection:
    def __init__(
        self,
        uuid: str,
        source_node_id: str,
        source_handle: str,
        target_node_id: str,
        target_handle: str,
        context: ConnectionContext,
    ):
        self.uuid = uuid
        self.source_node_id = source_node_id
        self.source_handle = source_handle
        self.target_node_id = target_node_id
        self.target_handle = target_handle
        self._touched: bool = False
        self._killer: bool = False
        self.context = context

    def touch(self):
        self._touched = True

    def make_killer(self):
        print("Making killer", self.uuid)
        self._killer = True

    def resurrect(self):
        self._killer = False

    def is_killer(self) -> bool:
        return self._killer

    def to_dict(self):
        return {
            "uuid": self.uuid,
            "source_node_id": self.source_node_id,
            "source_handle": self.source_handle,
            "target_node_id": self.target_node_id,
            "target_handle": self.target_handle,
            "touched": self._touched,
            "killer": self._killer
        }

    def get_source_node(self) -> "ExecutableNode":
        return self.context.state.get_node_by_id(self.source_node_id)

    def get_target_node(self) -> "ExecutableNode":
        return self.context.state.get_node_by_id(self.target_node_id)