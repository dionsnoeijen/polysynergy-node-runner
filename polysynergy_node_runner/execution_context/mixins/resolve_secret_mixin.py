import os
import re

from polysynergy_node_runner.execution_context.context import Context


class ResolveSecretMixin:
    context: Context

    def _replace_secret_placeholders(self, data: str) -> str:

        SECRET_PATTERN = re.compile(r"<secret:([a-zA-Z0-9_\-]+)>")

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
                if not val.startswith("<secret:"):
                    continue
                replaced = self._replace_secret_placeholders(data=val)

                print("REPLACING SECRET:", attr_name, "with", replaced)

                setattr(self, attr_name, replaced)

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