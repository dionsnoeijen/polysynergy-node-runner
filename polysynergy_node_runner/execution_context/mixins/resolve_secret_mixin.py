import os
import re

from polysynergy_node_runner.execution_context.context import Context


class ResolveSecretMixin:
    context: Context

    def _replace_secret_placeholders(self, data: str) -> str:

        # Support both <secret:...> and <sec:...> patterns
        SECRET_PATTERN = re.compile(r"<sec(?:ret)?:([a-zA-Z0-9_\-]+)>")

        def replacer(match):
            secret_key = match.group(1)
            project_id = os.getenv("PROJECT_ID")
            if not project_id:
                raise ValueError("PROJECT_ID environment variable is not set")

            effective_stage = self.context.get_effective_stage()
            secret = self.context.secrets.get_secret_by_key(secret_key, project_id, effective_stage)

            if not secret or not secret.get("value"):
                value = "<SECRET::NOT::FOUND>"
            else:
                value = secret["value"]

            self.context.secrets_map[secret_key] = secret
            return value

        return SECRET_PATTERN.sub(replacer, data)

    def _resolve_secret(self):
        for attr_name in getattr(type(self), '__annotations__', {}):
            if attr_name.startswith("_"):
                continue
            val = getattr(self, attr_name, None)
            if isinstance(val, str):
                # Check for both <secret:...> and <sec:...> patterns
                if "<secret:" not in val and "<sec:" not in val:
                    continue
                replaced = self._replace_secret_placeholders(data=val)
                setattr(self, attr_name, replaced)
            elif isinstance(val, dict):
                # Process dict values for secrets (mutate in place)
                for k, v in val.items():
                    if isinstance(v, str) and ("<secret:" in v or "<sec:" in v):
                        val[k] = self._replace_secret_placeholders(v)

        if not self.__class__.__name__.startswith("VariableSecret"):
            return

        secret_key = getattr(self, "true_path", None)
        if not secret_key:
            return

        project_id = os.getenv("PROJECT_ID", None)
        if not project_id:
            raise ValueError("PROJECT_ID environment variable is not set")

        effective_stage = self.context.get_effective_stage()
        secret = self.context.secrets.get_secret_by_key(secret_key, project_id, effective_stage)

        if not secret or not secret.get("value"):
            secret = '<SECRET::NOT::FOUND>'

        self.context.secrets_map[secret_key] = secret
        setattr(self, "true_path", secret.get("value"))