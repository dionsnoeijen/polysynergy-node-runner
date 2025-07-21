from polysynergy_node_runner.execution_context.replace_placeholders import replace_placeholders


class PlaceholderReplacementMixin:
    def _apply_placeholder_replacements(self):
        for attr_name in getattr(type(self), '__annotations__', {}):
            if attr_name.startswith("_"):
                continue
            val = getattr(self, attr_name, None)
            if isinstance(val, (str, dict, list)):
                replaced = replace_placeholders(data=val, values=self.__dict__, state=self.state)
                setattr(self, attr_name, replaced)