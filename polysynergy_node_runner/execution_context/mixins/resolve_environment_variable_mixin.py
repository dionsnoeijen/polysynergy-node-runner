import os
import re

from polysynergy_node_runner.execution_context.context import Context


class ResolveEnvironmentVariableMixin:

    context: Context

    def _replace_environment_placeholders(self, data: str) -> str:

        ENV_PATTERN = re.compile(r"<environment:([a-zA-Z0-9_\-]+)>")

        def replacer(match):
            env_key = match.group(1)
            project_id = os.getenv("PROJECT_ID")
            if not project_id:
                raise ValueError("PROJECT_ID environment variable is not set")

            effective_stage = self.context.get_effective_stage()
            value = self.context.env_vars.get_var(project_id, effective_stage, env_key)

            if not value:
                value = "<ENV_VAR::NOT::FOUND>"

            return value

        return ENV_PATTERN.sub(replacer, data)

    def _resolve_environment_variable(self):
        # Handle string attributes that may contain <environment:key> pattern
        for attr_name in getattr(type(self), '__annotations__', {}):
            if attr_name.startswith("_"):
                continue
            val = getattr(self, attr_name, None)
            if isinstance(val, str):
                if "<environment:" not in val:
                    continue
                replaced = self._replace_environment_placeholders(data=val)
                setattr(self, attr_name, replaced)

        # Handle VariableEnvironment nodes (existing functionality)
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