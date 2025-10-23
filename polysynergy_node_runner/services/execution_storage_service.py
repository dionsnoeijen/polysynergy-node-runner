import json
import os
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any, Optional, Callable

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

    def clear_previous_execution(self, flow_id: str, current_run_id: str = None, *, max_runs_to_keep: int = 50, **extra_kwargs):
        """
        Clear old execution data while preserving the last X runs.
        
        Args:
            flow_id: The flow identifier
            current_run_id: The current run ID to preserve (optional)
            max_runs_to_keep: Maximum number of runs to keep (default: 50)
        """
        
        try:
            # Get current highest run number before cleanup
            current_max_run_number = self._get_max_run_number(flow_id)
            next_run_number = current_max_run_number + 1
            
            # Store the run number for this run_id  
            if not hasattr(self, '_current_run_numbers'):
                self._current_run_numbers = {}
            if current_run_id:
                self._current_run_numbers[current_run_id] = next_run_number
            
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

    def _get_max_run_number(self, flow_id: str) -> int:
        """Get the highest run_number from existing runs"""
        try:
            # Use query instead of scan since we have the partition key
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(flow_id)
            )
            
            max_run_number = 0
            
            # Process all items to find highest run_number
            for item in response.get('Items', []):
                sk = item.get('SK', '')
                if '#' in sk and 'connections' not in sk and 'mock_nodes' not in sk and 'data' in item:
                    try:
                        data = json.loads(item.get('data', '{}'))
                        if 'run_number' in data:
                            max_run_number = max(max_run_number, int(data['run_number']))
                    except (json.JSONDecodeError, ValueError, KeyError):
                        pass  # Skip items with invalid data
            
            # Handle pagination
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression=Key("PK").eq(flow_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    sk = item.get('SK', '')
                    if '#' in sk and 'connections' not in sk and 'mock_nodes' not in sk and 'data' in item:
                        try:
                            data = json.loads(item.get('data', '{}'))
                            if 'run_number' in data:
                                max_run_number = max(max_run_number, int(data['run_number']))
                        except (json.JSONDecodeError, ValueError, KeyError):
                            pass
            
            return max_run_number
            
        except Exception as e:
            print(f"Error getting max run number: {e}")
            return 0

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
            # Add node metadata for easier reconstruction
            "node_id": node.id,
            "order": order,
            "handle": node.handle,
            "type": node.path.split(".")[-1] if node.path else "Unknown",
            "run_id": run_id,
        }
        
        # Add run_number if this is the first node (order 0) of the run
        if order == 0 and hasattr(self, '_current_run_numbers') and run_id in self._current_run_numbers:
            result_data["run_number"] = self._current_run_numbers[run_id]

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
        """Get list of available runs for a flow with metadata - OPTIMIZED"""
        # Use query instead of scan since we have the partition key - dramatically faster
        try:
            response = self.table.query(
                KeyConditionExpression=Key("PK").eq(flow_id)
            )
            
            runs_metadata = {}
            
            # Process all items in one pass instead of multiple scans
            for item in response.get('Items', []):
                sk = item.get('SK', '')
                if '#' in sk:
                    parts = sk.split('#')
                    run_id = parts[0]
                    
                    # Track run IDs and extract metadata
                    if run_id not in runs_metadata:
                        runs_metadata[run_id] = {
                            "run_id": run_id,
                            "timestamp": run_id  # Default fallback
                        }
                    
                    # If this is a node result (not connections/mock_nodes), extract timestamp and run_number
                    if (len(parts) >= 3 and 
                        'connections' not in sk and 
                        'mock_nodes' not in sk and 
                        'data' in item):
                        try:
                            data = json.loads(item.get('data', '{}'))
                            if 'timestamp' in data:
                                runs_metadata[run_id]["timestamp"] = data["timestamp"]
                            if 'run_number' in data:
                                runs_metadata[run_id]["run_number"] = data["run_number"]
                        except (json.JSONDecodeError, KeyError):
                            pass  # Keep default timestamp if parsing fails
            
            # Handle pagination efficiently
            while 'LastEvaluatedKey' in response:
                response = self.table.query(
                    KeyConditionExpression=Key("PK").eq(flow_id),
                    ExclusiveStartKey=response['LastEvaluatedKey']
                )
                for item in response.get('Items', []):
                    sk = item.get('SK', '')
                    if '#' in sk:
                        parts = sk.split('#')
                        run_id = parts[0]
                        
                        if run_id not in runs_metadata:
                            runs_metadata[run_id] = {
                                "run_id": run_id,
                                "timestamp": run_id
                            }
                        
                        if (len(parts) >= 3 and 
                            'connections' not in sk and 
                            'mock_nodes' not in sk and 
                            'data' in item):
                            try:
                                data = json.loads(item.get('data', '{}'))
                                if 'timestamp' in data:
                                    runs_metadata[run_id]["timestamp"] = data["timestamp"]
                                if 'run_number' in data:
                                    runs_metadata[run_id]["run_number"] = data["run_number"]
                            except (json.JSONDecodeError, KeyError):
                                pass
            
            # Sort and return
            runs = list(runs_metadata.values())
            runs.sort(key=lambda x: x["timestamp"], reverse=True)
            return runs
            
        except Exception as e:
            print(f"Error getting available runs: {e}")
            return []

    def _make_sk(self, run_id: str, node_id: str, order: int, stage: str, sub_stage: str) -> str:
        return f"{run_id}#{node_id}#{order}#{stage}#{sub_stage}"

    def find_node_order(self, flow_id: str, run_id: str, node_id: str) -> int | None:
        try:
            resp = self.table.query(
                KeyConditionExpression=Key("PK").eq(flow_id) &
                                       Key("SK").begins_with(f"{run_id}#{node_id}#"),
                Limit=1,  # we hebben er maar één nodig
            )
            items = resp.get("Items", [])
            if not items:
                return None
            sk = items[0]["SK"]
            parts = sk.split("#")  # [run_id, node_id, order, stage, sub_stage]
            return int(parts[2]) if len(parts) >= 3 else None
        except Exception as e:
            print(f"find_node_order error: {e}")
            return None

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

    def upsert_node_fields(
        self,
        flow_id: str,
        run_id: str,
        node_id: str,
        order: int,
        patch: Dict[str, Any],
        *,
        stage: str = "mock",
        sub_stage: str = "mock",
        mutate: Optional[Callable[[dict], None]] = None,
    ):
        """
        Fetch existing node result JSON, apply a shallow/deep patch, then write it back.
        - `patch` merges into root of the stored JSON (we'll do a shallow merge + a
          special-case for 'variables' dict).
        - `mutate` lets you apply arbitrary custom changes to the loaded dict.
        Idempotent: same PK/SK → overwrite the single item.
        """
        sk = self._make_sk(run_id, node_id, order, stage, sub_stage)

        # 1) read current
        current: dict = {}
        try:
            resp = self.table.get_item(Key={"PK": flow_id, "SK": sk})
            item = resp.get("Item")
            if item and "data" in item:
                current = json.loads(item["data"])
        except Exception as e:
            print(f"upsert_node_fields get_item error: {e}")

        # Guard: Don't create new records via upsert - only update existing ones
        # This prevents creating incomplete records when tool hooks try to store results
        # before the node has been executed via state_execute()
        if not current:
            print(f"⚠️  upsert_node_fields: No existing record for node {node_id} (order={order}), skipping upsert to prevent incomplete record creation")
            return

        # 2) merge patch
        merged = deepcopy(current) if isinstance(current, dict) else {}
        for k, v in (patch or {}).items():
            if k == "variables" and isinstance(v, dict):
                # special: merge variables dict shallowly
                merged.setdefault("variables", {})
                if isinstance(merged["variables"], dict):
                    merged["variables"].update(v)
                else:
                    merged["variables"] = v
            else:
                merged[k] = v

        # 3) optional mutate hook (e.g. deep edits)
        if mutate:
            try:
                mutate(merged)
            except Exception as e:
                print(f"upsert_node_fields mutate error: {e}")

        # 4) write back
        try:
            self.table.put_item(Item={
                "PK": flow_id,
                "SK": sk,
                "data": json.dumps(merged, default=str),
            })
        except Exception as e:
            print(f"upsert_node_fields put_item error: {e}")

    def set_node_variable_value(
        self,
        flow_id: str,
        run_id: str,
        node_id: str,
        order: int | None,
        true_text: str,
        *,
        stage: str = "mock",
        sub_stage: str = "mock",
        handle: str = 'true_path'
    ):
        """
        Convenience: set variables.true_path while preserving all other fields.
        If order is None, we'll try to discover it.
        """
        if order is None:
            order = self.find_node_order(flow_id, run_id, node_id)
            if order is None:
                # If we really can't find it, default to 0 (or bail out)
                print(f"set_node_true_path: could not find order for {node_id}, defaulting to 0")
                order = 0

        self.upsert_node_fields(
            flow_id=flow_id,
            run_id=run_id,
            node_id=node_id,
            order=order,
            stage=stage,
            sub_stage=sub_stage,
            patch={"variables": {handle: true_text}},
        )

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