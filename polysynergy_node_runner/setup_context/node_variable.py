from typing import Any, get_origin, Union, get_args
from dataclasses import dataclass

from polysynergy_nodes.base.setup_context.node_variable_settings import NodeVariableSettings
from polysynergy_nodes.base.setup_context.path_settings import PathSettings


@dataclass
class NodeVariable:
    name: str
    handle: str
    value: Any = None
    type: str = "string"
    has_in: bool = False
    has_out: bool = False
    has_dock: bool = False
    published: bool = False
    published_title: str = ""
    published_description: str = ""
    out_type_override: str | None = None
    in_type_override: str | None = None
    dock: dict[str, Any] | None = None
    node: bool = True  # Indicates if the variable is shown in the node
    info: str | None = None
    group: str | None = None
    metadata: dict[str, Any] | None = None

    @staticmethod
    def create_from_property(instance: Any, name: str, attr: NodeVariableSettings) -> "NodeVariable":
        cls_annotations = getattr(instance.__class__, '__annotations__', {})
        var_type = cls_annotations.get(name, None)

        if var_type is None:
            variable_type_str = "str"
        elif hasattr(var_type, "__name__"):
            variable_type_str = var_type.__name__
        elif hasattr(var_type, "_name") and var_type._name:
            variable_type_str = var_type._name
        else:
            variable_type_str = str(var_type)

        try:
            value = getattr(instance, name, attr.default)
        except Exception:
            value = None

        return NodeVariable(
            name=name.replace('_', ' ').title(),
            handle=name,
            value=value,
            type=variable_type_str,
            has_dock=bool(attr.dock),
            published=attr.published,
            published_title=attr.published_title,
            published_description=attr.published_description,
            dock=attr.dock,
            has_in=attr.has_in,
            has_out=attr.has_out,
            out_type_override=attr.out_type_override,
            in_type_override=attr.in_type_override,
            node=attr.node,
            info=attr.info,
            group=attr.group,
            metadata=attr.metadata or {}
        )

    from typing import Any, get_origin, get_args, Union

    @staticmethod
    def add_path_variable(instance: Any, path_attr: str) -> "NodeVariable":
        """
        Zorgt ervoor dat 'true_path' en 'false_path' correct worden geïnterpreteerd.
        - Begin **altijd** met 'true_path' of 'false_path'.
        - Als er extra types zijn, voeg die toe als "| type1 | type2 | ...".
        """
        if not hasattr(instance, path_attr):
            return None

        value = getattr(instance, path_attr)

        settings = getattr(type(instance), path_attr, None)
        label = None
        info = None
        default = value

        if isinstance(settings, PathSettings):
            label = settings.label or None
            info = settings.info or None
            default = settings.default

        var_type = path_attr

        cls_annotations = getattr(instance.__class__, '__annotations__', {})
        annotated_type = cls_annotations.get(path_attr, None)

        if annotated_type:
            if get_origin(annotated_type) is Union:
                sub_types = [t.__name__ if hasattr(t, "__name__") else str(t) for t in get_args(annotated_type)]
                var_type += " | " + " | ".join(sub_types)
            else:
                var_type += f" | {annotated_type.__name__}" if hasattr(annotated_type, "__name__") else f" | {str(annotated_type)}"

        return NodeVariable(
            name=label or path_attr.replace("_", " ").title(),
            handle=path_attr,
            value=default,
            type=var_type,
            has_out=True,
            info=info
        )

    def to_dict(self):
        result = {
            "name": self.name,
            "handle": self.handle,
            "value": [] if isinstance(self.value, dict) and not self.value else self.value,
            "type": self.type,
            "has_in": self.has_in,
            "has_out": self.has_out,
            "has_dock": self.has_dock,
            "node": self.node,
            "out_type_override": self.out_type_override,
            "in_type_override": self.in_type_override,
            "published": self.published,
            "published_title": self.published_title,
            "published_description": self.published_description,
            "info": self.info,
            "group": self.group,
            "metadata": self.metadata or {}
        }

        if self.has_dock:
            result["dock"] = self.dock

        return result
