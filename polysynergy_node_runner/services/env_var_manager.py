from collections import defaultdict

import boto3
import os


class EnvVarManager:
    def __init__(self, access_key: str = None, secret_key: str = None, region: str = None):
        execution_env = os.getenv("AWS_EXECUTION_ENV", "")

        is_lambda = execution_env.lower().startswith("aws_lambda")
        is_explicit = bool(access_key and secret_key and not is_lambda)

        if is_explicit:
            self.client = boto3.client(
                "dynamodb",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key
            )
        else:
            self.client = boto3.client("dynamodb", region_name=region)

        self.table_name = os.getenv("DYNAMODB_ENV_VARS_TABLE", "polysynergy_env_vars")

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
            grouped[key][stage] = {
                'value': item["value"]["S"],
                'id': item["PK"]["S"]
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
        self.client.put_item(
            TableName=self.table_name,
            Item={
                "PK": {"S": pk},
                "value": {"S": value}
            }
        )
        return {"id": pk, "key": key, "stage": stage, "value": value}

    def get_var(self, project_id, stage, key):
        pk = self._key(project_id, stage, key)
        response = self.client.get_item(
            TableName=self.table_name,
            Key={"PK": {"S": pk}}
        )
        item = response.get("Item")
        if not item:
            return None

        return item.get("value", {}).get("S")

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
