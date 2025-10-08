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


def find_nodes_until_backwards(
    start_node: "ExecutableNode",
    match_end_node_fn: Callable[["ExecutableNode"], bool],
    get_node_by_id: Callable[[str], "ExecutableNode"],
    skip_node_fn: Callable[["ExecutableNode"], bool] = None,
    post_process_fn: Callable[["ExecutableNode"], None] = None
):
    """
    Traverse backwards through the flow using incoming connections.
    Similar to find_nodes_until but traverses upstream instead of downstream.
    """
    visited = set()
    collected_nodes = []
    end_node = None

    def traverse(node):
        nonlocal end_node
        if node.id in visited:
            return
        visited.add(node.id)

        # Use get_in_connections() instead of get_out_connections() for backwards traversal
        for connection in node.get_in_connections():
            source_node = get_node_by_id(connection.source_node_id)
            if source_node is None:
                continue

            if match_end_node_fn(source_node):
                end_node = source_node
                continue

            if skip_node_fn and skip_node_fn(source_node):
                continue

            if post_process_fn:
                post_process_fn(source_node)

            collected_nodes.append(source_node)
            traverse(source_node)

    traverse(start_node)
    return collected_nodes, end_node


def find_node_by_handle_backwards(
    start_node: "ExecutableNode",
    target_handle: str,
    get_node_by_id: Callable[[str], "ExecutableNode"]
) -> "ExecutableNode":
    """
    Find a node with the specified handle by traversing backwards through the flow.
    Returns the first node found with the target handle, or None if not found.
    """
    def match_handle_fn(node):
        return node.handle == target_handle

    collected_nodes, end_node = find_nodes_until_backwards(
        start_node=start_node,
        match_end_node_fn=match_handle_fn,
        get_node_by_id=get_node_by_id
    )

    # Return the end_node if found, or check collected nodes
    if end_node:
        return end_node

    # Check collected nodes for the handle (in case it wasn't the endpoint)
    for node in collected_nodes:
        if node.handle == target_handle:
            return node

    return None