import os

from polysynergy_node_runner.execution_context.context import Context


class ResolveEnvironmentVariableMixin:

    context: Context

    def _resolve_environment_variable(self):
        if not self.__class__.__name__.startswith("VariableEnvironment"):
            return

        variable_key = getattr(self, "true_path", None)
        if not variable_key:
            return

        project_id = os.getenv("PROJECT_ID", None)
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")

        effective_stage = self.context.get_effective_stage()
        value = self.context.env_vars.get_var(project_id, effective_stage, variable_key)

        if not value:
            value = '<ENV_VAR::NOT::FOUND>'

        setattr(self, "true_path", value)