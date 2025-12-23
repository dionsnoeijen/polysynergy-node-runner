from polysynergy_node_runner.execution_context.context import Context
from polysynergy_node_runner.execution_context.replace_placeholders import replace_placeholders


class PlaceholderReplacementMixin:

    context: Context
    _replace_secret_placeholders: callable
    _replace_environment_placeholders: callable

    def _apply_placeholder_replacements(self):
        # Skip path output variables - they are outputs, not inputs
        skip_attrs = {'true_path', 'false_path'}

        # Get skip_template settings from node variable settings
        node_var_settings = getattr(type(self), '__node_variable_settings__', {})

        for attr_name in getattr(type(self), '__annotations__', {}):
            if attr_name.startswith("_") or attr_name in skip_attrs:
                continue

            # Check if this variable has skip_template=True
            var_settings = node_var_settings.get(attr_name, {})
            if var_settings.get('skip_template', False):
                continue

            val = getattr(self, attr_name, None)
            if isinstance(val, str):
                replaced = self._replace_secret_placeholders(data=val)
                replaced = self._replace_environment_placeholders(data=replaced)
                replaced = replace_placeholders(data=replaced, values=self.__dict__, state=self.context.state, current_node=self)
                setattr(self, attr_name, replaced)
            elif isinstance(val, (dict, list)):
                replaced = replace_placeholders(data=val, values=self.__dict__, state=self.context.state, current_node=self)
                setattr(self, attr_name, replaced)
