from __future__ import annotations


class Flow:
    def __init__(
        self,
        connections,
        state,
        execution_flow,
        node_setup_version_id,
        run_id,
    ):
        self.nodes = {}
        self.handle_nodes = {}
        self.connections = connections
        self.state = state
        self.execution_flow = execution_flow
        self.node_setup_version_id = node_setup_version_id
        self.run_id = run_id
        # For secret resolution, the original values are stored,
        # so they can be placed back after execution (and the secret does not get exposed)
        self.secrets_map = {}

    def make_json_serializable(self, value):
        if isinstance(value, (str, int, float, bool, type(None))):
            return value

        if isinstance(value, bytes):
            try:
                return value.decode("utf-8")  # Probeer te decoderen als UTF-8 tekst
            except UnicodeDecodeError:
                return f"<non‐serializable bytes:{len(value)}>"  # Als het geen tekst is, geef een indicatie

        if isinstance(value, (list, tuple)):
            return [self.make_json_serializable(v) for v in value]

        if isinstance(value, dict):
            return {k: self.make_json_serializable(v) for k, v in value.items()}

        return f"<non‐serializable {type(value).__name__}>"


    async def execute_node(self, node):
        if node.is_blocking():
            print('Is blocking:', node.id, node.handle, node.__class__.__name__)
            return

        if node.is_pending():
            print('Is pending:', node.id, node.handle, node.__class__.__name__)
            return

        if not node.is_killed() and self.should_kill_node(node):
            print('Killing node:', node.handle, node.__class__.__name__)
            node.kill(self.execution_flow)
            return

        if node.is_processed() or node.is_killed():
            print('ALREADY PROCESSED:', node.id, node.handle, node.__class__.__name__)
            return

        if (node.is_driven() or node.has_in_connections()) and not self.all_connections_processed(node.id):
            await self.traverse_backward(node, node.is_in_loop())

        if not node.is_processed() and not node.is_killed():
            for conn in self.get_driving_connections(node.id):
                node.apply_from_driving_connection(conn)

            for conn in self.get_alive_in_connections(node.id):
                node.apply_from_incoming_connection(conn)

            print('Executing:', node.id, node.handle, node.__class__.__name__)
            node.run_id = self.run_id
            await node.state_execute(self.execution_flow)

        await self.traverse_forward(node)

    async def traverse_backward(self, node, loop_origin=None):
        connections = self.get_driving_connections(node.id) + self.get_in_connections(node.id)

        for conn in connections:
            source_node = self.nodes[conn.source_node_id]

            conn.touch()

            print(
                'Traversing backward:',
                node.handle, node.__class__.__name__,
                '<-',
                source_node.handle, source_node.__class__.__name__,
            )

            if conn.is_killer() or node.was_found_by(conn.uuid):
                continue

            if not source_node.is_processed() and not source_node.is_killed():
                await self.execute_node(source_node)


    async def traverse_forward(self, node):
        for conn in self.get_out_connections(node.id):
            target_node = self.nodes[conn.target_node_id]

            conn.touch()
            if conn.is_killer():
                continue
            if not target_node.is_processed() and not target_node.is_killed():
                print(
                    'Traversing forward:',
                    node.handle, node.__class__.__name__,
                    '->',
                    target_node.handle, target_node.__class__.__name__
                )
                target_node.add_found_by(conn.uuid)
                if self.should_kill_node(target_node):
                    print('Killing node:', target_node.handle, target_node.__class__.__name__)
                    target_node.kill(self.execution_flow)
                    continue
                if node.is_in_loop():
                    target_node.set_in_loop(node.is_in_loop())
                await self.execute_node(target_node)

    def should_kill_node(self, node):
        driving_connections = node.get_driving_connections()
        if driving_connections and all(conn.is_killer() for conn in driving_connections):
            return True

        in_conns = self.get_in_connections(node.id)

        if len(in_conns) == 1:
            return in_conns[0].is_killer()

        handle_groups = {}
        for conn in in_conns:
            handle = conn.target_handle
            handle_groups.setdefault(handle, []).append(conn)

        for handle, conns in handle_groups.items():
            if all(conn.is_killer() for conn in conns):
                print('Killing node, ALL IN CONS ARE KILLER:', node.handle, node.__class__.__name__)
                return True

        return False

    def get_driving_connections(self, node_id):
        return [c for c in self.connections if
                c.target_node_id == node_id and c.target_handle in ("node", "a", "b")]

    def get_in_connections(self, node_id):
        return [c for c in self.connections if c.target_node_id == node_id and c.target_handle not in ("node", "a", "b")]

    def get_alive_in_connections(self, node_id):
        return [
            c for c in self.connections
            if c.target_node_id == node_id
               and c.target_handle not in ("node", "a", "b")
               and not c.is_killer()
        ]

    def get_out_connections(self, node_id):
        return [c for c in self.connections if c.source_node_id == node_id]

    def get_out_connections_except_on_false_path(self, node_id):
        return [c for c in self.connections if c.source_node_id == node_id and c.source_handle != "false_path"]

    def get_out_connections_on_true_path(self, node_id):
        return [c for c in self.connections if c.source_node_id == node_id and c.source_handle == "true_path"]

    def get_out_connections_on_false_path(self, node_id):
        return [c for c in self.connections if c.source_node_id == node_id and c.source_handle == "false_path"]

    def all_connections_processed(self, node_id):
        for conn in self.get_driving_connections(node_id):
            source_node = self.nodes[conn.source_node_id]
            if not source_node.is_processed():
                return False

        for conn in self.get_in_connections(node_id):
            source_node = self.nodes[conn.source_node_id]
            if not source_node.is_processed():
                return False
        return True

    def register_node(self, node):
        self.nodes[node.id] = node
        self.state.register_node(node)
        if node.handle:
            self.handle_nodes[node.handle] = node

    def get_node(self, id_or_handle: str) -> "ExecutableNode":
        node = self.nodes.get(id_or_handle) or self.handle_nodes.get(id_or_handle)
        return node