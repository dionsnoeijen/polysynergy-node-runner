import logging
import os
import threading
from pubnub.pnconfiguration import PNConfiguration
from pubnub.pubnub import PubNub

pnconfig = PNConfiguration()
pnconfig.publish_key = os.getenv('PUBNUB_PUBLISH_KEY', 'your-publish-key')
pnconfig.subscribe_key = os.getenv('PUBNUB_SUBSCRIBE_KEY', 'your-subscribe-key')
pnconfig.secret_key = os.getenv('PUBNUB_SECRET_KEY', 'your-secret-key')
pnconfig.user_id = os.getenv('USER_ID', 'poly_synergy_flow')

# Stel timeouts laag in om blokkeren te vermijden
pnconfig.connect_timeout = 2
pnconfig.request_timeout = 2

pubnub = PubNub(pnconfig)

logger = logging.getLogger(__name__)

def send_flow_event(flow_id: str, run_id: str, node_id: str | None, event_type: str, order: int = -1, status='running'):

    message = {
        'flow_id': flow_id,
        'run_id': run_id,
        'node_id': node_id,
        'event': event_type,
        'order': order,
        'status': status,
    }

    if not pnconfig.publish_key or pnconfig.publish_key == 'your-publish-key':
        logger.error("PUBNUB_PUBLISH_KEY is missing or default")
    if not pnconfig.subscribe_key or pnconfig.subscribe_key == 'your-subscribe-key':
        logger.error("PUBNUB_SUBSCRIBE_KEY is missing or default")

    def fire():
        try:
            pubnub.publish().channel(f'flow-{flow_id}').message(message).sync()
        except Exception as e:
            logger.info(f"[PubNub] publish failed (ignored): {e}")

    threading.Thread(target=fire).start()