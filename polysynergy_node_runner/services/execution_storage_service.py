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

    def clear_previous_execution(self, flow_id: str, *args, **extra_kwargs):
        """
        Clear old execution data while preserving the last X runs.
        """
        current_run_id = args[0] if args else None
        max_runs_to_keep = 50
        
        try:
            # Get all run_ids for this flow
            run_ids = self._get_all_run_ids(flow_id)
            
            # Always clear current run data first to avoid stale state
            if current_run_id and current_run_id in run_ids:
                run_ids.remove(current_run_id)
            
            # Sort by timestamp (newest first)
            run_ids.sort(reverse=True)
            
            # Keep only the most recent runs
            runs_to_delete = run_ids[max_runs_to_keep:]
            
            # Delete old runs
            if runs_to_delete:
                self._delete_runs(flow_id, runs_to_delete)
                
        except Exception as e:
            print(f"Error in retention logic: {e}")
            # Fall back to clearing all data
            self._clear_all_execution_data(flow_id)

    def _get_all_run_ids(self, flow_id: str) -> list[str]:
        """Get all unique run_ids for a flow_id using scan to avoid query issues"""
        try:
            # Use table resource scan instead of client to avoid format issues
            response = self.table.scan(
                FilterExpression='PK = :flow_id',
                ExpressionAttributeValues={':flow_id': flow_id}
            )
            
            run_ids = set()
            for item in response.get('Items', []):
                sk = item.get('SK', '')
                if '#' in sk:
                    run_id = sk.split('#')[0]
                    run_ids.add(run_id)
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='PK = :flow_id',
                    ExpressionAttributeValues={':flow_id': flow_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    sk = item.get('SK', '')
                    if '#' in sk:
                        run_id = sk.split('#')[0]
                        run_ids.add(run_id)
            
            return list(run_ids)
            
        except Exception as e:
            print(f"Error getting run IDs: {e}")
            return []

    def _delete_runs(self, flow_id: str, run_ids_to_delete: list[str]):
        """Delete all data for specific run_ids using scan and delete"""
        try:
            # Use table resource scan instead of client
            response = self.table.scan(
                FilterExpression='PK = :flow_id',
                ExpressionAttributeValues={':flow_id': flow_id}
            )
            
            items_to_delete = []
            for item in response.get('Items', []):
                sk = item.get('SK', '')
                if '#' in sk:
                    run_id = sk.split('#')[0]
                    if run_id in run_ids_to_delete:
                        items_to_delete.append({
                            'PK': item['PK'],
                            'SK': sk
                        })
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='PK = :flow_id',
                    ExpressionAttributeValues={':flow_id': flow_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    sk = item.get('SK', '')
                    if '#' in sk:
                        run_id = sk.split('#')[0]
                        if run_id in run_ids_to_delete:
                            items_to_delete.append({
                                'PK': item['PK'],
                                'SK': sk
                            })
            
            # Delete in batches
            if items_to_delete:
                with self.table.batch_writer() as batch:
                    for item in items_to_delete:
                        batch.delete_item(Key={"PK": item['PK'], "SK": item['SK']})
                        
        except Exception as e:
            print(f"Error deleting runs: {e}")

    def _clear_all_execution_data(self, flow_id: str):
        """Fallback method that clears all execution data (original behavior)"""
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

    def store_mock_nodes_result(self, flow_id: str, run_id: str, mock_nodes: list[dict]):
        """Store the final mock nodes state for perfect visual state recreation"""
        self.table.put_item(Item={
            "PK": flow_id,
            "SK": f"{run_id}#mock_nodes",
            "data": json.dumps(mock_nodes, default=str)
        })

    def get_connections_result(self, flow_id: str, run_id: str):
        response = self.table.get_item(
            Key={"PK": flow_id, "SK": f"{run_id}#connections"}
        )
        item = response.get("Item", {})
        return json.loads(item["data"]) if "data" in item else None

    def get_mock_nodes_result(self, flow_id: str, run_id: str):
        """Get the stored mock nodes state for perfect visual state recreation"""
        response = self.table.get_item(
            Key={"PK": flow_id, "SK": f"{run_id}#mock_nodes"}
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

    def get_available_runs(self, flow_id: str) -> list[dict]:
        """Get list of available runs for a flow with metadata"""
        run_ids = self._get_all_run_ids(flow_id)
        
        # Sort runs by ID (which should be timestamp-based)
        run_ids.sort(reverse=True)
        
        runs = []
        for run_id in run_ids:
            # Get some metadata for the run (e.g., first node execution timestamp)
            run_info = {
                "run_id": run_id,
                "timestamp": run_id  # Assuming run_id contains timestamp info
            }
            
            # Try to get the first node result to extract more metadata
            first_node_result = self._get_first_node_result(flow_id, run_id)
            if first_node_result and "timestamp" in first_node_result:
                run_info["timestamp"] = first_node_result["timestamp"]
            
            runs.append(run_info)
        
        return runs

    def get_all_nodes_for_run(self, flow_id: str, run_id: str, stage: str = "mock", sub_stage: str = "mock") -> list[dict]:
        """Get all node execution results for a specific run"""
        try:
            # Use table resource scan to get all nodes for this run
            response = self.table.scan(
                FilterExpression='PK = :flow_id AND begins_with(SK, :run_prefix) AND NOT contains(SK, :connections)',
                ExpressionAttributeValues={
                    ':flow_id': flow_id,
                    ':run_prefix': f"{run_id}#",
                    ':connections': '#connections'
                }
            )
            
            nodes = []
            for item in response.get('Items', []):
                sk = item.get('SK', '')
                # Parse the SK to extract node info: run_id#node_id#order#stage#sub_stage
                parts = sk.split('#')
                if len(parts) >= 3:
                    node_data = json.loads(item.get('data', '{}'))
                    node_info = {
                        'node_id': parts[1] if len(parts) > 1 else '',
                        'order': int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
                        'data': node_data
                    }
                    nodes.append(node_info)
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='PK = :flow_id AND begins_with(SK, :run_prefix) AND NOT contains(SK, :connections)',
                    ExpressionAttributeValues={
                        ':flow_id': flow_id,
                        ':run_prefix': f"{run_id}#",
                        ':connections': '#connections'
                    },
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    sk = item.get('SK', '')
                    parts = sk.split('#')
                    if len(parts) >= 3:
                        node_data = json.loads(item.get('data', '{}'))
                        node_info = {
                            'node_id': parts[1] if len(parts) > 1 else '',
                            'order': int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
                            'data': node_data
                        }
                        nodes.append(node_info)
            
            # Sort by order
            nodes.sort(key=lambda x: x['order'])
            return nodes
            
        except Exception as e:
            print(f"Error getting all nodes for run: {e}")
            return []

    def _get_first_node_result(self, flow_id: str, run_id: str) -> dict:
        """Get the first node result for a run to extract metadata"""
        try:
            # Use table resource scan instead of client
            response = self.table.scan(
                FilterExpression='PK = :flow_id',
                ExpressionAttributeValues={':flow_id': flow_id}
            )
            
            for item in response.get('Items', []):
                sk = item.get('SK', '')
                # Check if this item belongs to our run_id and is not connections
                if sk.startswith(f"{run_id}#") and "#connections" not in sk:
                    if 'data' in item:
                        return json.loads(item['data'])
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression='PK = :flow_id',
                    ExpressionAttributeValues={':flow_id': flow_id},
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    sk = item.get('SK', '')
                    if sk.startswith(f"{run_id}#") and "#connections" not in sk:
                        if 'data' in item:
                            return json.loads(item['data'])
            
            return {}
        except Exception as e:
            print(f"Error getting first node result: {e}")
            return {}

    def clear_all_runs(self, flow_id: str):
        """Clear all execution data for a flow"""
        self._clear_all_execution_data(flow_id)

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