from polysynergy_node_runner.execution_context.execution_state import ExecutionState


class ConnectionContext:
    def __init__(self, state: ExecutionState):
        self.state = state