from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.flow_state import FlowState
from polysynergy_node_runner.execution_context.mixins.apply_from_connection_mixin import ApplyFromConnectionMixin
from polysynergy_node_runner.execution_context.mixins.connection_logic_mixin import ConnectionLogicMixin
from polysynergy_node_runner.execution_context.mixins.flow_execution_mixin import FlowExecutionMixin
from polysynergy_node_runner.execution_context.mixins.placeholder_replacement_mixin import PlaceholderReplacementMixin
from polysynergy_node_runner.execution_context.mixins.resolve_environment_variable_mixin import \
    ResolveEnvironmentVariableMixin
from polysynergy_node_runner.execution_context.mixins.resolve_secret_mixin import ResolveSecretMixin
from polysynergy_node_runner.execution_context.mixins.resurrect_mixin import ResurrectMixin
from polysynergy_node_runner.execution_context.mixins.state_lifecyclye_mixin import StateLifecycleMixin
from polysynergy_node_runner.execution_context.mixins.traversal_mixin import TraversalMixin
from polysynergy_node_runner.execution_context.utils.make_serializable import make_json_serializable

class ExecutableNode(
    ConnectionLogicMixin,
    StateLifecycleMixin,
    PlaceholderReplacementMixin,
    ResolveEnvironmentVariableMixin,
    ResolveSecretMixin,
    FlowExecutionMixin,
    ResurrectMixin,
    TraversalMixin,
    ApplyFromConnectionMixin
):
    flow_state: FlowState = FlowState.ENABLED
    run_id: str = None

    def __init__(
        self,
        id: str,
        handle: str,
        stateful: bool = True,
        context: Context = None
    ):
        self.context = context
        self.factory: callable = None

        self.id: str = id
        self.handle: str = handle

        # A stateless node is always fully recreated (via its factory) when the flow is resurrected.
        # This ensures the node starts with a clean slate and re-applies its initial values.
        # It's useful for nodes like VariableJson that must re-evaluate dynamic inputs
        # or placeholders on each iteration.

        # Stateless mode is *not* the default because some nodes (like secrets, API calls,
        # or cached computations) are expensive or side-effectful. In those cases, it's more
        # efficient to reuse the same instance and simply reset its flow state.
        self.stateful = stateful

        self._driving_connections = []
        self._in_connections = []
        self._out_connections = []
        self._killed = False
        self._processed = False
        self._blocking = False
        self._found_by = []
        self._exception = None
        self._in_loop: ExecutableNode | None = None

    def to_dict(self):
        vars_dict = {}

        for a in type(self).__annotations__:
            if not a.startswith("_"):
                raw_value = getattr(self, a, None)
                vars_dict[a] = make_json_serializable(raw_value)
        return vars_dict


