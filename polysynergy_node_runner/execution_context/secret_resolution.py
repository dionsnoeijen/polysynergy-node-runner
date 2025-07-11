from polysynergy_nodes.secret.services.secrets_manager import SecretsManager


def is_secret_ref(value: str) -> bool:
    return isinstance(value, str) and "arn:aws:secretsmanager" in value

def resolve_secret_value(value: str) -> str:
    try:
        return SecretsManager().get_secret(value)["value"]
    except Exception:
        return value  # fallback

def resolve_secrets_in_structure(obj):
    if isinstance(obj, dict):
        return {k: resolve_secrets_in_structure(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_secrets_in_structure(v) for v in obj]
    elif is_secret_ref(obj):
        return resolve_secret_value(obj)
    return obj