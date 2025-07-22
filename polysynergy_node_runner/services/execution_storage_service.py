import json
import os
from datetime import datetime

import boto3
from boto3.dynamodb.conditions import Key

from polysynergy_node_runner.execution_context.utils.redact_secrets import redact
from polysynergy_node_runner.execution_context.utils.truncate_values import truncate_large_values


class DynamoDbExecutionStorageService:
    def __init__(
        self,
        table_name: str = "execution_storage",
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
    ):
        self.table_name = table_name

        is_lambda = (
            "AWS_EXECUTION_ENV" in os.environ
            and os.environ["AWS_EXECUTION_ENV"].lower().startswith("aws_lambda")
        )
        region = region or os.getenv("AWS_REGION", "eu-central-1")

        if access_key and secret_key and not is_lambda:
            self.dynamodb = boto3.resource(
                "dynamodb",
                region_name=region,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            )
        else:
            self.dynamodb = boto3.resource("dynamodb", region_name=region)

        self.table = self.dynamodb.Table(self.table_name)

    def clear_previous_execution(self, flow_id: str):
        exclusive_start_key = None

        while True:
            kwargs = {
                "KeyConditionExpression": Key("PK").eq(flow_id)
            }
            if exclusive_start_key:
                kwargs["ExclusiveStartKey"] = exclusive_start_key

            response = self.table.query(**kwargs)
            items = response.get("Items", [])

            with self.table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(Key={"PK": flow_id, "SK": item["SK"]})

            if "LastEvaluatedKey" in response:
                exclusive_start_key = response["LastEvaluatedKey"]
            else:
                break

    def store_connections_result(self, flow_id: str, run_id: str, connections: list[dict]):
        self.table.put_item(Item={
            "PK": flow_id,
            "SK": f"{run_id}#connections",
            "data": json.dumps(connections)
        })

    def get_connections_result(self, flow_id: str, run_id: str):
        response = self.table.get_item(
            Key={"PK": flow_id, "SK": f"{run_id}#connections"}
        )
        item = response.get("Item", {})
        return json.loads(item["data"]) if "data" in item else None

    def store_node_result(self,
        node,
        flow_id: str,
        run_id: str,
        order: int,
        stage: str,
        sub_stage: str = 'mock'
    ):
        result_data = {
            "timestamp": datetime.now().isoformat(),
            "variables": redact(
                truncate_large_values(node.to_dict()),
                {
                    secret.get("value"): secret
                    for secret in getattr(node.context, "secrets_map", {}).values()
                    if secret.get("value")
                }
            ),
            "error_type": type(node.get_exception()).__name__ if node.get_exception() else None,
            "error": str(node.get_exception()) if node.get_exception() else None,
            "killed": node.is_killed(),
            "processed": node.is_processed(),
        }

        self.table.put_item(Item={
            "PK": flow_id,
            "SK": f"{run_id}#{node.id}#{order}#{stage}#{sub_stage}",
            "data": json.dumps(result_data, default=str),
        })

    def get_node_result(
        self,
        flow_id: str,
        run_id: str,
        node_id: str,
        order: int,
        stage: str = "",
        sub_stage: str = ""
    ):
        print('Retrieving node result:', flow_id, run_id, node_id, order, stage, sub_stage)

        response = self.table.get_item(
            Key={
                "PK": flow_id,
                "SK": f"{run_id}#{node_id}#{order}#{stage}#{sub_stage}"
            }
        )
        item = response.get("Item", {})
        return json.loads(item["data"]) if "data" in item else None

def get_execution_storage_service(
    table_name: str = "execution_storage"
) -> DynamoDbExecutionStorageService:
    region = os.getenv("AWS_REGION") or "eu-central-1"
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    return DynamoDbExecutionStorageService(
        table_name=table_name,
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )

def get_execution_storage_service_from_env(
    access_key: str,
    secret_key: str,
    region: str,
    table_name: str = "execution_storage"
) -> DynamoDbExecutionStorageService:
    return DynamoDbExecutionStorageService(
        table_name=table_name,
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )