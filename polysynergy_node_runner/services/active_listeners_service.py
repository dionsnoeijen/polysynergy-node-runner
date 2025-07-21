import os
import uuid
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Key


class ActiveListenersService:
    _listener_cache: dict[str, bool] = {}

    def __init__(
        self,
        table_name: str = "flow_listeners",
        access_key: str | None = None,
        secret_key: str | None = None,
        region: str | None = None,
    ):
        self.table_name = table_name
        is_lambda = os.getenv("AWS_EXECUTION_ENV", "").lower().startswith("aws_lambda")
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

    def set_listener(self, node_setup_version_id: str, stage: str = "mock"):
        item = {
            "PK": node_setup_version_id,
            "listener_id": str(uuid.uuid4()),
            "stage": stage,
            "last_activated_at": datetime.now(timezone.utc).isoformat()
        }
        self.table.put_item(Item=item)

    def _cache_key(self, node_setup_version_id: str, required_stage: str) -> str:
        return f"{node_setup_version_id}@{required_stage}"

    def has_listener(self, node_setup_version_id: str, required_stage: str = "mock", max_age_minutes: int = 60) -> bool:
        key = self._cache_key(node_setup_version_id, required_stage)
        if key in self._listener_cache:
            return self._listener_cache[key]

        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(node_setup_version_id)
        )

        items = response.get("Items", [])
        if not items:
            self._listener_cache[key] = False
            return False

        item = items[0]
        if item.get("stage") != required_stage:
            self._listener_cache[key] = False
            return False

        timestamp = item.get("last_activated_at")
        if not timestamp:
            self._listener_cache[key] = False
            return False

        try:
            last_active = datetime.fromisoformat(timestamp)
            now = datetime.now(timezone.utc)
            is_valid = now - last_active < timedelta(minutes=max_age_minutes)
            self._listener_cache[key] = is_valid
            return is_valid
        except Exception:
            self._listener_cache[key] = False
            return False

    def clear_listeners(self, node_setup_version_id: str):
        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(node_setup_version_id)
        )
        with self.table.batch_writer() as batch:
            for item in response.get("Items", []):
                batch.delete_item(Key={"PK": node_setup_version_id})

    def is_listener_valid(self, node_setup_version_id: str, max_age_minutes: int = 60) -> bool:
        response = self.table.query(
            KeyConditionExpression=Key("PK").eq(node_setup_version_id)
        )
        items = response.get("Items", [])
        if not items:
            return False

        timestamp = items[0].get("last_activated_at")
        if not timestamp:
            return False

        try:
            last_active = datetime.fromisoformat(timestamp)
            now = datetime.now(timezone.utc)
            return now - last_active < timedelta(minutes=max_age_minutes)
        except Exception:
            return False

def get_active_listeners_service(
    table_name: str = "flow_listeners"
) -> ActiveListenersService:
    return ActiveListenersService(table_name=table_name)

def get_active_listeners_service_from_env(
    access_key: str,
    secret_key: str,
    region: str,
    table_name: str = "flow_listeners"
) -> ActiveListenersService:
    return ActiveListenersService(
        table_name=table_name,
        access_key=access_key,
        secret_key=secret_key,
        region=region
    )
