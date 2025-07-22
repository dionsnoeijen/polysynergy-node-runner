import os
import json
import threading
import logging
import redis

logger = logging.getLogger(__name__)

_redis = None

def get_redis():
    global _redis
    if _redis is None:
        _redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=0
        )
    return _redis

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

    def fire():
        try:
            redis_conn = get_redis()
            print('[Redis] Publishing message:', message)
            redis_conn.publish(f"execution_updates:{flow_id}", json.dumps(message))
        except Exception as e:
            logger.warning(f"[Redis] publish failed (ignored): {e}")

    threading.Thread(target=fire).start()