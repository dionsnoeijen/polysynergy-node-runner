from polysynergy_node_runner.execution_context.execution_state import ExecutionState
from polysynergy_node_runner.execution_context.flow import Flow
from polysynergy_node_runner.services.active_listeners_service import ActiveListenersService
from polysynergy_node_runner.services.env_var_manager import EnvVarManager
from polysynergy_node_runner.services.execution_storage_service import DynamoDbExecutionStorageService
from polysynergy_node_runner.services.secrets_manager import SecretsManager


class Context:
    run_id: str = None

    def __init__(
        self,
        run_id: str,
        node_setup_version_id: str,
        state: ExecutionState,
        flow: Flow,
        storage: DynamoDbExecutionStorageService,
        active_listeners: ActiveListenersService,
        secrets_manager: SecretsManager,
        env_var_manager: EnvVarManager,
        stage: str = 'mock',
        sub_stage: str = 'mock',
        execution_flow: dict[str, any] = None,
        trigger_node_id: str = None,
    ):
        self.run_id = run_id
        self.node_setup_version_id = node_setup_version_id
        self.state = state
        self.flow = flow
        self.storage = storage
        self.active_listeners = active_listeners
        self.secrets = secrets_manager
        self.env_vars = env_var_manager
        self.stage = stage
        self.sub_stage = sub_stage
        self.execution_flow = execution_flow or {}
        self.trigger_node_id = trigger_node_id

        # For secret resolution, the original values are stored,
        # so they can be placed back after execution
        # (and the secret does not get exposed)
        self.secrets_map = {}

    def get_effective_stage(self):
        return (
            self.sub_stage
            if self.stage == "mock" and self.sub_stage != "mock"
            else self.stage
        )
