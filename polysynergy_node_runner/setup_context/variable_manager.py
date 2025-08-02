from polysynergy_node_runner.setup_context.node_variable_settings import NodeVariableSettings
from polysynergy_node_runner.setup_context.node_variable import NodeVariable


class VariableManager:
    """Handles variable generation and management for Node instances."""
    
    def __init__(self, node):
        self.node = node
    
    def generate_node_variables(self) -> list[NodeVariable]:
        """Generate NodeVariable instances from NodeVariableSettings attributes."""
        variables = []
        
        # Find NodeVariableSettings in the immediate class
        for name, attr in vars(type(self.node)).items():
            if isinstance(attr, NodeVariableSettings):
                try:
                    variables.append(NodeVariable.create_from_property(self.node, name, attr))
                except AttributeError:
                    print(f"Property '{name}' can not be retrieved {self.node.__class__.__name__}")

        # Handle path variables
        for path_attr in ["true_path", "false_path"]:
            if hasattr(self.node, path_attr):
                path_variable = NodeVariable.add_path_variable(self.node, path_attr)
                if path_variable:
                    variables.append(path_variable)

        return variables