class ExecutionState:
    def __init__(self):
        self.nodes_by_id = {}
        self.nodes_by_handle = {}
        self.nodes: list = []
        self.connections: list = []

    def register_node(self, node):
        self.nodes_by_id[node.id] = node
        self.nodes_by_handle[node.handle] = node
        self.nodes.append(node)

    def get_node_by_id(self, node_id):
        return self.nodes_by_id.get(node_id)

    def get_node_by_handle(self, handle):
        return self.nodes_by_handle.get(handle)

    def get_connection_source_variable(self, connection):
        source_node = self.get_node_by_id(connection.source_node_id)
        path_parts = connection.source_handle.split(".")

        current = source_node
        for part in path_parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)

            if current is None:
                break

        return current

    def resolve_state_value(self, key: str):
        parts = key.split(".")
        handle = parts.pop(0)
        node = self.get_node_by_handle(handle)
        if not node:
            return f"<missing node: {handle}>"

        value = getattr(node, parts.pop(0), None)
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, f"<missing key: {key}>")
            else:
                return f"<non-dict access on: {key}>"
        return value

def get_execution_state():
    return ExecutionState()