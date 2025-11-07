import os

import boto3
from botocore.exceptions import ClientError

class SecretsManager:
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = None):
        execution_env = os.getenv("AWS_EXECUTION_ENV", "")

        print(f"Initializing SecretsManager with region: {region}, access_key: {'***' if access_key else 'None'}, execution_env: {execution_env}")

        is_lambda = execution_env.lower().startswith("aws_lambda")
        is_explicit = bool(access_key and secret_key and not is_lambda)

        # Initialize Secrets Manager client (for fallback)
        if is_explicit:
            self.client = boto3.client(
                "secretsmanager",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=os.getenv("AWS_SESSION_TOKEN")
            )
            # Initialize DynamoDB client with same credentials
            self.dynamodb = boto3.client(
                "dynamodb",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=os.getenv("AWS_SESSION_TOKEN")
            )
        else:
            self.client = boto3.client("secretsmanager", region_name=region)
            self.dynamodb = boto3.client("dynamodb", region_name=region)

        self.dynamodb_table = os.getenv("SECRETS_TABLE_NAME", "project_secrets")

    def _prefix_name(self, name: str, project_id: str, stage: str | None = None) -> str:
        if stage:
            return f"{project_id}@{stage}@{name}"
        return f"{project_id}@{name}"

    def create_secret(self, name: str, secret_value: str, project_id: str, stage: str) -> dict:
        full_name = self._prefix_name(name, project_id, stage)
        try:
            # Write to DynamoDB (new primary storage)
            self.dynamodb.put_item(
                TableName=self.dynamodb_table,
                Item={
                    'secret_key': {'S': full_name},
                    'secret_value': {'S': secret_value},
                    'project_id': {'S': project_id},
                    'stage': {'S': stage},
                    'created_at': {'S': '2025-11-03T06:45:00Z'}
                }
            )

            # Return success response in same format as Secrets Manager
            return {
                'ARN': f'dynamodb:{full_name}',
                'Name': full_name,
                'VersionId': 'v1'
            }
        except Exception as e:
            raise e

    def get_secret_by_key(self, key: str, project_id: str, stage: str) -> dict:
        full_name = self._prefix_name(key, project_id, stage)
        return self.get_secret(full_name)

    def get_secret(self, secret_id: str) -> dict:
        # Try DynamoDB first (cheap!)
        try:
            response = self.dynamodb.get_item(
                TableName=self.dynamodb_table,
                Key={'secret_key': {'S': secret_id}}
            )

            if 'Item' in response:
                secret_value = response['Item'].get('secret_value', {}).get('S')

                full_key = secret_id
                if "@" in full_key:
                    key = full_key.split("@", 1)[1]
                else:
                    key = full_key

                return {
                    "key": key,
                    "value": secret_value
                }
        except Exception as e:
            print(f"DynamoDB read failed for {secret_id}, falling back to Secrets Manager: {e}")

        # Fallback to AWS Secrets Manager
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
            # Update in DynamoDB
            self.dynamodb.update_item(
                TableName=self.dynamodb_table,
                Key={'secret_key': {'S': secret_id}},
                UpdateExpression='SET secret_value = :val',
                ExpressionAttributeValues={':val': {'S': secret_value}}
            )

            return {
                'ARN': f'dynamodb:{secret_id}',
                'Name': secret_id,
                'VersionId': 'v2'
            }
        except Exception as e:
            raise e

    def update_secret_by_key(self, key: str, new_value: str, project_id: str, stage: str) -> dict:
        full_name = self._prefix_name(key, project_id, stage)
        return self.update_secret(full_name, new_value)

    def delete_secret(self, secret_id: str, force_delete_without_recovery: bool = True) -> dict:
        try:
            # Delete from DynamoDB
            self.dynamodb.delete_item(
                TableName=self.dynamodb_table,
                Key={'secret_key': {'S': secret_id}}
            )

            return {
                'ARN': f'dynamodb:{secret_id}',
                'Name': secret_id,
                'DeletionDate': '2025-11-03T06:45:00Z'
            }
        except Exception as e:
            raise e

    def delete_secret_by_key(self, key: str, project_id: str, stage: str, force_delete_without_recovery: bool = True) -> dict:
        full_name = self._prefix_name(key, project_id, stage)
        return self.delete_secret(full_name, force_delete_without_recovery)

    def list_secrets(self, project_id: str) -> list:
        try:
            # Scan DynamoDB for all secrets with this project_id
            response = self.dynamodb.scan(
                TableName=self.dynamodb_table,
                FilterExpression='project_id = :pid',
                ExpressionAttributeValues={':pid': {'S': project_id}}
            )

            # Convert DynamoDB format to Secrets Manager format
            secrets = []
            for item in response.get('Items', []):
                secrets.append({
                    'Name': item.get('secret_key', {}).get('S', ''),
                    'ARN': f"dynamodb:{item.get('secret_key', {}).get('S', '')}",
                    'Tags': [
                        {'Key': 'project', 'Value': project_id},
                        {'Key': 'stage', 'Value': item.get('stage', {}).get('S', '')}
                    ]
                })

            return secrets
        except Exception as e:
            print(f"DynamoDB list failed, falling back to Secrets Manager: {e}")
            # Fallback to Secrets Manager
            try:
                response = self.client.list_secrets(
                    Filters=[
                        {'Key': 'tag-key', 'Values': ['project']},
                        {'Key': 'tag-value', 'Values': [project_id]}
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