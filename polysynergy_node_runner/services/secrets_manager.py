import os

import boto3
from botocore.exceptions import ClientError

class SecretsManager:
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = None):
        execution_env = os.getenv("AWS_EXECUTION_ENV", "")

        print(f"Initializing SecretsManager with region: {region}, access_key: {'***' if access_key else 'None'}, execution_env: {execution_env}")

        is_lambda = execution_env.lower().startswith("aws_lambda")
        is_explicit = bool(access_key and secret_key and not is_lambda)

        if is_explicit:
            self.client = boto3.client(
                "secretsmanager",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=os.getenv("AWS_SESSION_TOKEN")
            )
        else:
            self.client = boto3.client("secretsmanager", region_name=region)

    def _prefix_name(self, name: str, project_id: str, stage: str | None = None) -> str:
        if stage:
            return f"{project_id}@{stage}@{name}"
        return f"{project_id}@{name}"

    def create_secret(self, name: str, secret_value: str, project_id: str, stage: str) -> dict:
        full_name = self._prefix_name(name, project_id, stage)
        try:
            kwargs = {
                "Name": full_name,
                "SecretString": secret_value,
                "Tags": [
                    {"Key": "project", "Value": project_id},
                    {"Key": "stage", "Value": stage}
                ]
            }
            return self.client.create_secret(**kwargs)
        except ClientError as e:
            raise e

    def get_secret_by_key(self, key: str, project_id: str, stage: str) -> dict:
        full_name = self._prefix_name(key, project_id, stage)
        return self.get_secret(full_name)

    def get_secret(self, secret_id: str) -> dict:
        try:
            response = self.client.get_secret_value(SecretId=secret_id)

            full_key = response.get("Name", "")
            if "@" in full_key:
                key = full_key.split("@", 1)[1]
            else:
                key = full_key

            return {
                "key": key,
                "value": response.get("SecretString")
            }

        except ClientError as e:
            raise e

    def update_secret(self, secret_id: str, secret_value: str) -> dict:
        try:
            response = self.client.update_secret(
                SecretId=secret_id,
                SecretString=secret_value
            )
            return response
        except ClientError as e:
            raise e

    def update_secret_by_key(self, key: str, new_value: str, project_id: str, stage: str) -> dict:
        full_name = self._prefix_name(key, project_id, stage)
        try:
            return self.client.update_secret(
                SecretId=full_name,
                SecretString=new_value
            )
        except ClientError as e:
            raise e

    def delete_secret(self, secret_id: str, force_delete_without_recovery: bool = True) -> dict:
        try:
            response = self.client.delete_secret(
                SecretId=secret_id,
                ForceDeleteWithoutRecovery=force_delete_without_recovery
            )
            return response
        except ClientError as e:
            raise e

    def delete_secret_by_key(self, key: str, project_id: str, stage: str, force_delete_without_recovery: bool = True) -> dict:
        full_name = self._prefix_name(key, project_id, stage)
        try:
            return self.client.delete_secret(
                SecretId=full_name,
                ForceDeleteWithoutRecovery=force_delete_without_recovery
            )
        except ClientError as e:
            raise e

    def list_secrets(self, project_id: str) -> list:
        try:
            response = self.client.list_secrets(
                Filters=[
                    {
                        'Key': 'tag-key',
                        'Values': ['project']
                    },
                    {
                        'Key': 'tag-value',
                        'Values': [project_id]
                    }
                ]
            )
            return response.get("SecretList", [])
        except ClientError as e:
            raise e

def get_secrets_manager() -> SecretsManager:
    region = os.getenv("AWS_REGION") or "eu-central-1"
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    return SecretsManager(
        region=region,
        access_key=access_key,
        secret_key=secret_key
    )

def get_secrets_manager_from_env(access_key: str, secret_key: str, region: str) -> SecretsManager:
    return SecretsManager(
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )