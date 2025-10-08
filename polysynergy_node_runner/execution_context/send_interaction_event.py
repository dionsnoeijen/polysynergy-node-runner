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

async def send_interaction_event_async(
    flow_id: str,
    run_id: str,
    node_id: str,
    interaction_type: str,
    data: dict = None,
    tenant_id: str = None,
    user_id: str = None
):
    """
    Send an interaction event to the frontend via WebSocket.

    Args:
        flow_id: ID of the flow
        run_id: ID of the current run
        node_id: ID of the node requesting interaction
        interaction_type: Type of interaction (e.g. 'oauth_authorization_required')
        data: Additional data for the interaction (e.g. auth_url, service_name)
        tenant_id: Tenant ID for routing
        user_id: User ID for routing
    """
    message = {
        'type': 'interaction_event',
        'flow_id': flow_id,
        'run_id': run_id,
        'node_id': node_id,
        'interaction_type': interaction_type,
        'data': data or {},
        'tenant_id': tenant_id,
        'user_id': user_id,
    }

    print('SEND INTERACTION EVENT (async)', message)

    try:
        redis_conn = await get_async_redis()

        # Publish to flow-specific channel for WebSocket routing
        channel = f"interaction_events:{flow_id}"
        if tenant_id:
            channel = f"interaction_events:{tenant_id}:{flow_id}"

        # Fire and forget - don't await the publish
        asyncio.create_task(
            redis_conn.publish(channel, json.dumps(message))
        )
    except Exception as e:
        logger.warning(f"[Redis] async interaction event publish failed (ignored): {e}")

def send_interaction_event(
    flow_id: str,
    run_id: str,
    node_id: str,
    interaction_type: str,
    data: dict = None,
    tenant_id: str = None,
    user_id: str = None
):
    """
    Synchronous version of send_interaction_event.
    """
    message = {
        'type': 'interaction_event',
        'flow_id': flow_id,
        'run_id': run_id,
        'node_id': node_id,
        'interaction_type': interaction_type,
        'data': data or {},
        'tenant_id': tenant_id,
        'user_id': user_id,
    }

    try:
        redis_conn = get_redis()

        # Publish to flow-specific channel for WebSocket routing
        channel = f"interaction_events:{flow_id}"
        if tenant_id:
            channel = f"interaction_events:{tenant_id}:{flow_id}"

        redis_conn.publish(channel, json.dumps(message))
    except Exception as e:
        logger.warning(f"[Redis] interaction event publish failed (ignored): {e}")