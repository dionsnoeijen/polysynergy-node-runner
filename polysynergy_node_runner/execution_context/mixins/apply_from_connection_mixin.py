from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.flow_state import FlowState


class ApplyFromConnectionMixin:
    flow_state: FlowState
    context: Context

    def apply_from_driving_connection(self, connection):
        if self.flow_state == FlowState.ENABLED:
            self.apply_from_incoming_connection(connection)
            return

        # Flow in means, try to apply the variables from the source
        # if they are the same, it will do so
        if self.flow_state != FlowState.FLOW_IN:
            return

        source_node = self.context.state.get_node_by_id(connection.source_node_id)
        source_attributes = list(getattr(type(source_node), '__annotations__', {}).keys())
        source_attributes = [a for a in source_attributes if not a.startswith("_")]

        for attr in source_attributes:
            if hasattr(self, attr):
                setattr(self, attr, getattr(source_node, attr))

    def apply_from_incoming_connection(self, connection):
        var = self.context.state.get_connection_source_variable(connection)
        self._apply_attribute(connection.target_handle, var)

    def _apply_attribute(self, property_name, value):
        if "." in property_name:
            parent_attr, sub_key = property_name.split(".", 1)
            parent_dict = getattr(self, parent_attr, {})

            if not isinstance(parent_dict, dict):
                raise TypeError(
                    f"Can't configure: '{parent_attr}' existing type is: {type(parent_dict).__name__}, not a dict!")

            parent_dict[sub_key] = value
            setattr(self, parent_attr, parent_dict)
        else:
            setattr(self, property_name, value)