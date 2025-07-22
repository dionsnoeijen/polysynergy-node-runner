from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from polysynergy_node_runner.execution_context.executable_node import ExecutableNode


def find_nodes_until(
    start_node: "ExecutableNode",
    match_end_node_fn: Callable[["ExecutableNode"], bool],
    get_node_by_id: Callable[[str], "ExecutableNode"],
    skip_node_fn: Callable[["ExecutableNode"], bool] = None,
    post_process_fn: Callable[["ExecutableNode"], None] = None
):
    visited = set()
    collected_nodes = []
    end_node = None

    def traverse(node):
        nonlocal end_node
        if node.id in visited:
            return
        visited.add(node.id)

        for connection in node.get_out_connections():
            target_node = get_node_by_id(connection.target_node_id)
            if target_node is None:
                continue

            if match_end_node_fn(target_node):
                end_node = target_node
                continue

            if skip_node_fn and skip_node_fn(target_node):
                continue

            if post_process_fn:
                post_process_fn(target_node)

            collected_nodes.append(target_node)
            traverse(target_node)

    traverse(start_node)
    return collected_nodes, end_node