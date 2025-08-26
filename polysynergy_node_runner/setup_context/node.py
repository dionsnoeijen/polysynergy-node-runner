from dataclasses import dataclass, field

from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.execution_context.flow_state import FlowState

from polysynergy_node_runner.setup_context.node_variable import NodeVariable
from polysynergy_node_runner.setup_context.file_resolver import FileResolver
from polysynergy_node_runner.setup_context.variable_manager import VariableManager
from polysynergy_node_runner.setup_context.connection_manager import ConnectionManager


@dataclass
class Node:
    id: str = ''
    context: Context = None
    state: ExecutionState = None
    flow: Flow = None

    handle: str = field(init=False, default=None)
    name: str = field(init=False, default='')
    path: str = field(init=False, default='')
    type: str = field(init=False, default='')
    icon: str = field(init=False, default='')
    category: str = field(init=False, default='')
    variables: list[NodeVariable] = field(init=False, default_factory=list)
    has_play_button: bool = field(init=False, default=False)
    has_enabled_switch: bool = field(init=False, default=True)
    stateful: bool = field(init=False, default=True)
    flow_state: FlowState = field(init=False, default=FlowState.ENABLED)
    version: float = field(init=False, default=1.0)
    metadata: dict = field(init=False, default_factory=dict)
    
    # Managers for composition
    _file_resolver: FileResolver = field(init=False, default=None)
    _variable_manager: VariableManager = field(init=False, default=None)
    _connection_manager: ConnectionManager = field(init=False, default=None)

    def resurrect(self):
        return self._connection_manager.resurrect()

    def _find_nodes_until(self, match_end_node_fn, skip_node_fn=None, post_process_fn=None):
        return self._connection_manager.find_nodes_until(match_end_node_fn, skip_node_fn, post_process_fn)

    def find_nodes_in_loop(self):
        return self._connection_manager.find_nodes_in_loop()

    def find_nodes_for_jump(self):
        return self._connection_manager.find_nodes_for_jump()

    def get_in_connections(self) -> list:
        return self._connection_manager.get_in_connections()

    def get_out_connections(self) -> list:
        return self._connection_manager.get_out_connections()

    def get_driving_connections(self) -> list:
        return self._connection_manager.get_driving_connections()

    def set_in_loop(self, loop: str | None):
        return self._connection_manager.set_in_loop(loop)

    def is_in_loop(self):
        return self._connection_manager.is_in_loop()

    def __post_init__(self):
        # Initialize managers
        self._file_resolver = FileResolver(self)
        self._variable_manager = VariableManager(self)
        self._connection_manager = ConnectionManager(self)
        
        # Generate variables using the manager
        self.variables = self._variable_manager.generate_node_variables()

    def _get_code(self):
        return self._file_resolver.get_code()

    def _get_documentation(self):
        return self._file_resolver.get_documentation()

    def _get_icon_content(self):
        return self._file_resolver.get_icon_content()

    def _get_declaring_file(self):
        return self._file_resolver.get_declaring_file()

    def to_dict(self):
        node_structure = {
            "handle": self.handle,
            "name": self.name,
            "path": self.path,
            "type": self.type,
            "icon": self._get_icon_content(),
            "category": self.category,
            "variables": [var.to_dict() for var in self.variables],
            "has_enabled_switch": self.has_enabled_switch,
            "has_documentation": self._get_documentation() is not None,
            "stateful": self.stateful,
            "default_flow_state": self.flow_state.value,
            "version": self.version,
            "metadata": self.metadata,
        }

        if self.has_play_button:
            node_structure["has_play_button"] = self.has_play_button

        # Note: Code field removed - using path-based discovery instead
        # node_structure["code"] = self._get_code()

        return node_structure