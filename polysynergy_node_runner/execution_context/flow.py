from __future__ import annotations

from polysynergy_node_runner.execution_context.executable_node import ExecutableNode


class Flow:
    def __init__(
        self,
        state,
        execution_flow,
        node_setup_version_id,
        run_id,
    ):
        self.state = state
        self.execution_flow = execution_flow
        self.node_setup_version_id = node_setup_version_id
        self.run_id = run_id

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
            return

        if (node.is_driven() or node.has_in_connections()) and not self.all_connections_processed(node.id):
            await self.traverse_backward(node)

        if not node.is_processed() and not node.is_killed():
            for conn in node.get_driving_connections():
                node.apply_from_driving_connection(conn)

            for conn in node.get_alive_in_connections():
                node.apply_from_incoming_connection(conn)

            print('Executing:', node.id, node.handle, node.__class__.__name__)
            node.run_id = self.run_id
            await node.state_execute(self.execution_flow)

        await self.traverse_forward(node)

    async def traverse_backward(self, node):
        connections = node.get_driving_connections() + node.get_in_connections()

        for conn in connections:
            source_node = conn.get_source_node()
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
        for conn in node.get_out_connections():
            target_node = conn.get_target_node()

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

        in_conns = node.get_in_connections()

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

    def all_connections_processed(self, node: "ExecutableNode") -> bool:
        for conn in node.get_driving_connections():
            source_node = conn.get_source_node()
            if not source_node.is_processed():
                return False

        for conn in node.get_in_connections():
            source_node = conn.get_source_node()
            if not source_node.is_processed():
                return False
        return True
