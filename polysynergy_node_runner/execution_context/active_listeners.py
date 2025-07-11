import os
import uuid
from datetime import datetime, timezone, timedelta

import boto3
from boto3.dynamodb.conditions import Key


class ActiveListenersService:
    _listener_cache: dict[str, bool] = {}

    def __init__(self):
        self.table_name = 'flow_listeners'
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

        item = items[0]
        timestamp = item.get("last_activated_at")
        if not timestamp:
            return False

        try:
            last_active = datetime.fromisoformat(timestamp)
            now = datetime.now(timezone.utc)
            return now - last_active < timedelta(minutes=max_age_minutes)
        except Exception:
            return False