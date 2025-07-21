def replace_node_to_executable(lines):
    for line in lines:
        yield line.replace("(Node):", "(ExecutableNode):").replace("(ServiceNode):", "(ExecutableNode):")
