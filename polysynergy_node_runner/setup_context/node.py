import importlib
from dataclasses import dataclass, field
from pathlib import Path

from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.execution_context.flow_state import FlowState

from polysynergy_node_runner.setup_context.node_variable import NodeVariable
from polysynergy_node_runner.setup_context.node_variable_settings import NodeVariableSettings


@dataclass
class Node:
    id: str = ''
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

    def resurrect(self):
        return

    def _find_nodes_until(self, match_end_node_fn, skip_node_fn=None, post_process_fn=None):
        return

    def find_nodes_in_loop(self):
        return

    def find_nodes_for_jump(self):
        return

    def get_driving_connections(self) -> list:
        return []

    def set_in_loop(self, loop: str | None):
        return

    def is_in_loop(self):
        return False

    def __post_init__(self):
        self.variables = self._generate_node_variables()

    def _generate_node_variables(self) -> list[NodeVariable]:
        variables = []
        for name, attr in vars(type(self)).items():
            if isinstance(attr, NodeVariableSettings):
                try:
                    variables.append(NodeVariable.create_from_property(self, name, attr))
                except AttributeError:
                    print(f"Property '{name}' can not be retrieved {self.__class__.__name__}")

        for path_attr in ["true_path", "false_path"]:
            if hasattr(self, path_attr):
                path_variable = NodeVariable.add_path_variable(self, path_attr)
                if path_variable:
                    variables.append(path_variable)

        return variables

    def _get_code(self):
        file_path = self._get_declaring_file()

        # print(f"Resolving code for {self.path} in {file_path}")

        if file_path and file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return None

    def _get_documentation(self):
        file_path = self._get_declaring_file()
        if file_path:
            doc_path = file_path.with_name(file_path.stem + "_README.md")
            if doc_path.exists():
                return doc_path.read_text(encoding="utf-8")
        return None

    def _get_icon_content(self):
        if not self.icon:
            return ""

        file_path = self._get_declaring_file()
        if file_path:
            icon_path = file_path.parent / "icons" / self.icon
            if icon_path.exists():
                return icon_path.read_text(encoding="utf-8")

        return self.icon

    def _get_declaring_file(self):
        try:
            module_path = ".".join(self.path.split(".")[:-1])
            module = importlib.import_module(module_path)
            return Path(module.__file__)
        except Exception as e:
            print(f"Can't resolve file for {self.path}: {e}")
            return None

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
            "documentation": self._get_documentation(),
            "stateful": self.stateful,
            "default_flow_state": self.flow_state.value,
            "version": self.version,
            "metadata": self.metadata,
        }

        if self.has_play_button:
            node_structure["has_play_button"] = self.has_play_button

        node_structure["code"] = self._get_code()

        return node_structure