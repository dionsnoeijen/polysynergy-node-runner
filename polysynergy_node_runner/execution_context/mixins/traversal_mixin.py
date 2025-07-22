from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.utils.traversal import find_nodes_until


class TraversalMixin:
    context: Context

    def find_nodes_for_jump(self):
        return find_nodes_until(
            self,
            get_node_by_id=self.context.state.get_node_by_id,
            match_end_node_fn=lambda node: node.__class__.__name__ == "Jump"
        )

    def find_nodes_in_loop(self):
        return find_nodes_until(
            self,
            match_end_node_fn=lambda node: node.__class__.__name__.startswith("LoopEnd"),
            get_node_by_id=self.context.state.get_node_by_id,
            skip_node_fn=lambda node: node.__class__.__name__.startswith("ListLoop"),
            post_process_fn=lambda node: node.set_in_loop(self)
        )