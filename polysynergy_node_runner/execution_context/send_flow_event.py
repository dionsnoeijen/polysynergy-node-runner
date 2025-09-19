import os
import json
import asyncio
import logging
import redis
import redis.asyncio as redis_async

logger = logging.getLogger(__name__)

_redis = None
_async_redis = None

def get_redis():
    """Get synchronous Redis connection for backward compatibility."""
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
    global _redis
    if _redis is None:
        _redis = redis.from_url(
            redis_url,
            decode_responses=True,
            db=0
        )
    return _redis

async def get_async_redis():
    """Get async Redis connection for non-blocking operations."""
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set")
    global _async_redis
    if _async_redis is None:
        _async_redis = await redis_async.from_url(
            redis_url,
            decode_responses=True,
            db=0
        )
    return _async_redis

async def send_flow_event_async(
    flow_id: str,
    run_id: str,
    node_id: str | None,
    event_type: str,
    order: int = -1,
    status='running'
):
    """Async version of send_flow_event for non-blocking event sending."""
    message = {
        'flow_id': flow_id,
        'run_id': run_id,
        'node_id': node_id,
        'event': event_type,
        'order': order,
        'status': status,
    }

    print('SEND FLOW EVENT (async)', message)
    
    try:
        redis_conn = await get_async_redis()
        # Fire and forget - don't await the publish
        asyncio.create_task(
            redis_conn.publish(f"execution_updates:{flow_id}", json.dumps(message))
        )
    except Exception as e:
        logger.warning(f"[Redis] async publish failed (ignored): {e}")

def send_flow_event(
    flow_id: str,
    run_id: str,
    node_id: str | None,
    event_type: str,
    order: int = -1,
    status='running'
):
    message = {
        'flow_id': flow_id,
        'run_id': run_id,
        'node_id': node_id,
        'event': event_type,
        'order': order,
        'status': status,
    }

    try:
        redis_conn = get_redis()
        redis_conn.publish(f"execution_updates:{flow_id}", json.dumps(message))
    except Exception as e:
        logger.warning(f"[Redis] publish failed (ignored): {e}")
