from polysynergy_nodes.secret.services.secrets_manager import SecretsManager


def is_secret_ref(value: str) -> bool:
    # Support both AWS Secrets Manager ARNs and DynamoDB ARNs
    return isinstance(value, str) and ("arn:aws:secretsmanager" in value or "dynamodb:" in value)

def resolve_secret_value(value: str) -> str:
    try:
        # Extract secret_id from ARN
        # Format: "arn:aws:secretsmanager:region:account:secret:secret_id" OR "dynamodb:secret_id"
        if value.startswith("dynamodb:"):
            secret_id = value.replace("dynamodb:", "")
        elif "arn:aws:secretsmanager" in value:
            # AWS Secrets Manager ARN format
            secret_id = value.split(":")[-1]
        else:
            secret_id = value

        return SecretsManager().get_secret(secret_id)["value"]
    except Exception as e:
        print(f"Failed to resolve secret {value}: {e}")
        return value  # fallback

def resolve_secrets_in_structure(obj):
    if isinstance(obj, dict):
        return {k: resolve_secrets_in_structure(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [resolve_secrets_in_structure(v) for v in obj]
    elif is_secret_ref(obj):
        return resolve_secret_value(obj)
    return obj