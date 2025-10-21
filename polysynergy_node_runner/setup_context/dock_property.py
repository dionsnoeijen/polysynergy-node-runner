def dock_property(
    enabled: bool = True,
    secret: bool = False,
    select_values: dict[str, str] | None = None,
    text_area: bool = False,
    rich_text_area: bool = False,
    code_editor: bool = False,
    handle: bool = False,
    json_editor: bool = False,
    switch: bool = False,
    info: str = "",
    metadata: dict | None = None,
    placeholder: str | None = None,
):
    return {
        "has_dock": True,
        "enabled": enabled,
        "secret": secret,
        "select_values": select_values,
        "text_area": text_area,
        "rich_text_area": rich_text_area,
        "code_editor": code_editor,
        "handle": handle,
        "json_editor": json_editor,
        "switch": switch,
        "info": info,
        "metadata": metadata or {},
        "placeholder": placeholder,
    }

def dock_code_editor(enabled: bool = True, info: str = "", metadata: dict | None = None):
    return {
        "has_dock": True,
        "enabled": enabled,
        "code_editor": True,
        "info": info,
        "metadata": metadata or {},
    }

def dock_switch(enabled: bool = True, info: str = ""):
    return {
        "has_dock": True,
        "enabled": enabled,
        "switch": True,
        "info": info,
    }

def dock_template_editor(enabled: bool = True, info: str = ""):
    return {
        "has_dock": True,
        "enabled": enabled,
        "template_editor": True,
        "info": info,
    }

def dock_json(enabled: bool = True, info: str = ""):
    return {
        "has_dock": True,
        "enabled": enabled,
        "json_editor": True,
        "info": info,
    }

def dock_files(enabled: bool = True, info: str = ""):
    return {
        "has_dock": True,
        "enabled": enabled,
        "files_editor": True,
        "info": info,
    }

def dock_select_values(select_values: dict[str, str], enabled: bool = True, info: str = ""):
    return {
        "has_dock": True,
        "enabled": enabled,
        "select_values": select_values,
        "info": info,
    }

def dock_text_area(enabled: bool = True, rich: bool = False, info: str = ""):
    return {
        "has_dock": True,
        "enabled": enabled,
        "text_area": not rich,
        "rich_text_area": rich,
        "info": info,
    }

def dock_dict(
    enabled: bool = True,
    key_label: str = "Key",
    value_label: str = "Value",
    type_label: str = "Type",
    type_field: bool = True,
    type_field_default: str = "str",
    in_switch: bool = True,
    in_switch_default: bool = False,
    in_switch_enabled: bool = True,
    in_type_override: str = None,
    out_switch: bool = True,
    out_switch_default: bool = False,
    out_switch_enabled: bool = True,
    out_type_override: str = None,
    key_field: bool = True,
    value_field: bool = True,
    info: str = "",
    metadata: dict | None = None,
):
    return {
        "has_dock": True,
        "enabled": enabled,
        "key_label": key_label,
        "value_label": value_label,
        "type_label": type_label,
        "type_field": type_field,
        "type_field_default": type_field_default,
        "in_switch": in_switch,
        "in_switch_default": in_switch_default,
        "in_switch_enabled": in_switch_enabled,
        "in_type_override": in_type_override,
        "out_switch": out_switch,
        "out_switch_default": out_switch_default,
        "out_switch_enabled": out_switch_enabled,
        "out_type_override": out_type_override,
        "key_field": key_field,
        "value_field": value_field,
        "info": info,
        "metadata": metadata or {},
    }