def redact(value, secrets_by_value):
    if isinstance(value, dict):
        return {k: redact(v, secrets_by_value) for k, v in value.items()}
    elif isinstance(value, list):
        return [redact(v, secrets_by_value) for v in value]
    elif isinstance(value, str):
        for secret_value, secret_obj in secrets_by_value.items():
            placeholder = f"<secret::{secret_obj['key']}>"
            if secret_value in value:
                value = value.replace(secret_value, placeholder)
        return value
    return value