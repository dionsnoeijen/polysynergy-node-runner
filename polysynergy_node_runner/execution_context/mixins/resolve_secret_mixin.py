import os

from polysynergy_node_runner.execution_context.context import Context


class ResolveSecretMixin:
    context: Context

    def _resolve_secret(self):
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