from polysynergy_nodes.base.setup_context.node import Node


class ServiceNode(Node):
    def provide_instance(self):
        raise NotImplementedError("Service nodes must implement `provides_instance()`")