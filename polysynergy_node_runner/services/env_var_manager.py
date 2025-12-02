from collections import defaultdict

import boto3
import os
from typing import Optional
from .encryption_service import get_encryption_service
from cryptography.fernet import InvalidToken


class EnvVarManager:
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = None):
        execution_env = os.getenv("AWS_EXECUTION_ENV", "")
        local_endpoint = os.getenv("DYNAMODB_LOCAL_ENDPOINT")

        is_lambda = execution_env.lower().startswith("aws_lambda")
        is_explicit = bool(access_key and secret_key and not is_lambda)

        if is_explicit:
            dynamodb_config = {
                "region_name": region,
                "aws_access_key_id": access_key,
                "aws_secret_access_key": secret_key
            }
            # Use local endpoint if configured
            if local_endpoint:
                dynamodb_config["endpoint_url"] = local_endpoint
                dynamodb_config["aws_access_key_id"] = "dummy"
                dynamodb_config["aws_secret_access_key"] = "dummy"

            self.client = boto3.client("dynamodb", **dynamodb_config)
        else:
            dynamodb_config = {"region_name": region}
            if local_endpoint:
                dynamodb_config["endpoint_url"] = local_endpoint
                dynamodb_config["aws_access_key_id"] = "dummy"
                dynamodb_config["aws_secret_access_key"] = "dummy"
            self.client = boto3.client("dynamodb", **dynamodb_config)

        self.table_name = os.getenv("DYNAMODB_ENV_VARS_TABLE", "polysynergy_env_vars")

        # Initialize encryption service
        try:
            self.encryption = get_encryption_service()
        except ValueError as e:
            print(f"Warning: Encryption service not available: {e}")
            self.encryption = None

    def _key(self, project_id, stage, key):
        return f"envvar#{project_id}#{stage}#{key}"

    def list_vars(self, project_id):
        response = self.client.scan(
            TableName=self.table_name,
            FilterExpression="begins_with(PK, :prefix)",
            ExpressionAttributeValues={":prefix": {"S": f"envvar#{project_id}#"}}
        )
        items = response.get("Items", [])
        grouped = defaultdict(dict)

        for item in items:
            _, project_id, stage, key = item["PK"]["S"].split("#", 3)
            value = item["value"]["S"]
            is_encrypted = item.get("encrypted", {}).get("BOOL", False)

            # Decrypt if encrypted
            if is_encrypted and self.encryption:
                try:
                    value = self.encryption.decrypt(value)
                except (InvalidToken, Exception) as e:
                    print(f"Warning: Failed to decrypt env var {key}: {e}")
                    value = "[DECRYPTION_FAILED]"

            grouped[key][stage] = {
                'value': value,
                'id': item["PK"]["S"],
                'encrypted': is_encrypted
            }

        result = [
            {
                "key": key,
                "project_id": project_id,
                "values": stages
            }
            for key, stages in grouped.items()
        ]
        return result

    def set_var(self, project_id, stage, key, value):
        pk = self._key(project_id, stage, key)

        # Encrypt value if encryption is available
        encrypted_value = value
        is_encrypted = False
        if self.encryption:
            try:
                encrypted_value = self.encryption.encrypt(value)
                is_encrypted = True
            except Exception as e:
                print(f"Warning: Failed to encrypt env var {key}: {e}. Storing as plain text.")

        self.client.put_item(
            TableName=self.table_name,
            Item={
                "PK": {"S": pk},
                "value": {"S": encrypted_value},
                "encrypted": {"BOOL": is_encrypted}
            }
        )
        return {"id": pk, "key": key, "stage": stage, "value": value, "encrypted": is_encrypted}

    def get_var(self, project_id, stage, key):
        pk = self._key(project_id, stage, key)
        response = self.client.get_item(
            TableName=self.table_name,
            Key={"PK": {"S": pk}}
        )
        item = response.get("Item")
        if not item:
            return None

        value = item.get("value", {}).get("S")
        is_encrypted = item.get("encrypted", {}).get("BOOL", False)

        # Decrypt if encrypted
        if is_encrypted and self.encryption:
            try:
                value = self.encryption.decrypt(value)
            except (InvalidToken, Exception) as e:
                print(f"Warning: Failed to decrypt env var {key}: {e}")
                return None

        return value

    def delete_var(self, project_id, stage, key):
        pk = self._key(project_id, stage, key)
        self.client.delete_item(
            TableName=self.table_name,
            Key={"PK": {"S": pk}}
        )

def get_env_var_manager():
    region = os.getenv("AWS_REGION") or "eu-central-1"
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    return EnvVarManager(
        region=region,
        access_key=access_key,
        secret_key=secret_key
    )

def get_env_var_manager_from_env(access_key: str, secret_key: str, region: str):
    return EnvVarManager(
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )
