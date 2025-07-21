from polysynergy_nodes import registered_nodes
from polysynergy_node_runner.execution_context.flow_state import FlowState


def node(
    name: str,
    category: str,
    icon: str | None = None,
    type: str = "rows",
    has_play_button: bool = False,
    has_enabled_switch: bool = True,
    stateful: bool = True,
    flow_state: FlowState = FlowState.ENABLED,
    version: float = 1.0,
    metadata: dict | None = None,
):
    def decorator(cls):
        original_init = cls.__post_init__ if hasattr(cls, "__post_init__") else lambda self: None

        def new_post_init(self, *args, **kwargs):
            self.name = name
            self.path = f"{cls.__module__}.{cls.__name__}"
            self.icon = icon
            self.type = type
            self.category = category
            self.has_play_button = has_play_button
            self.has_enabled_switch = has_enabled_switch
            self.stateful = stateful
            self.flow_state = flow_state
            self.version = version
            self.metadata = metadata or {}
            original_init(self)

        cls.__post_init__ = new_post_init
        cls._is_node = True

        return cls

    return decorator