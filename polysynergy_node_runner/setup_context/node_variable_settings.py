from polysynergy_node_runner.setup_context.dock_property import dock_property


class NodeVariableSettings:
    def __init__(
        self,
        label="",
        default=None,
        dock=None, # Show in dock?
        node=True, # Show in node?
        has_in=False,
        has_out=False,
        out_type_override=None,
        in_type_override=None,
        required=False,
        published=False,
        published_title=None,
        published_description=None,
        info: str | None=None,
        group: str | None = None,
        metadata: dict | None = None,
        type: str | None = None,
    ):
        self.label = label
        self.default = default
        self.dock = dock
        self.node = node
        if self.dock is True:
            self.dock = dock_property()
        self.has_in = has_in
        self.has_out = has_out
        self.out_type_override = out_type_override
        self.in_type_override = in_type_override
        self.required = required
        self.published = published
        self.published_title = published_title
        self.published_description = published_description
        self.info = info
        self.group = group
        self.metadata = metadata or {}
        self.type = type

    def __set_name__(self, owner, name):
        self.private_name = "_" + name

        if not hasattr(owner, '__node_variable_settings__'):
            owner.__node_variable_settings__ = {}
        owner.__node_variable_settings__[name] = {
            "label": self.label,
            "default": self.default,
            "dock": self.dock,
            "node": self.node,
            "has_in": self.has_in,
            "has_out": self.has_out,
            "out_type_override": self.out_type_override,
            "in_type_override": self.in_type_override,
            "required": self.required,
            "published": self.published,
            "published_title": self.published_title,
            "published_description": self.published_description,
            "info": self.info,
            "group": self.group,
            "metadata": self.metadata,
            "type": self.type,
        }

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, self.default)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, value)