import json
import os

import boto3
from boto3.dynamodb.conditions import Key

class DynamoDbExecutionStorageService:
    def __init__(self):
        self.table_name = 'execution_storage'
        is_lambda = os.getenv("AWS_EXECUTION_ENV") is not None

        if is_lambda:
            self.dynamodb = boto3.resource(
                "dynamodb",
                region_name=os.getenv("AWS_REGION", "eu-central-1"),
            )
        else:
            self.dynamodb = boto3.resource(
                "dynamodb",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "eu-central-1"),
            )
        self.table = self.dynamodb.Table(self.table_name)

    def clear_previous_execution(
        self,
        flow_id:str,
    ):
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
        item = {
            "PK": flow_id,
            "SK": f"{run_id}#connections",
            "data": json.dumps(connections)
        }
        self.table.put_item(Item=item)

    def get_connections_result(self, flow_id: str, run_id: str):
        response = self.table.get_item(
            Key={"PK": flow_id, "SK": f"{run_id}#connections"}
        )
        item = response.get("Item", {})
        return json.loads(item["data"]) if "data" in item else None

    def store_node_result(
        self,
        flow_id: str,
        run_id: str,
        node_id: str,
        order: int,
        result: str,
        stage: str,
        sub_stage: str = 'mock'
    ):
        item = {
            "PK": flow_id,
            "SK": f"{run_id}#{node_id}#{order}#{stage}#{sub_stage if sub_stage is not None else 'mock'}",
            "data": result
        }
        self.table.put_item(Item=item)

    def get_node_result(
        self,
        flow_id: str,
        run_id: str,
        node_id: str,
        order: int,
        stage: str = "",
        sub_stage: str = ""
    ):
        print(
            'Retrieving node result:',
            'flow id:', flow_id,
            'run_id:', run_id,
            'node_id:', node_id,
            'order:', order,
            'stage:', stage,
            'sub_stage:', sub_stage
        )

        response = self.table.get_item(
            Key={
                "PK": flow_id,
                "SK": f"{run_id}#{node_id}#{order}#{stage}#{sub_stage}"
            }
        )
        item = response.get("Item", {})
        return json.loads(item["data"]) if "data" in item else None