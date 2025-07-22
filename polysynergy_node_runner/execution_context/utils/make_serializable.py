def make_json_serializable(value):
    if isinstance(value, (str, int, float, bool, type(None))):
        return value

    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return f"<non‐serializable bytes:{len(value)}>"

    if isinstance(value, (list, tuple)):
        return [make_json_serializable(v) for v in value]

    if isinstance(value, dict):
        return {k: make_json_serializable(v) for k, v in value.items()}

    return f"<non‐serializable {type(value).__name__}>"