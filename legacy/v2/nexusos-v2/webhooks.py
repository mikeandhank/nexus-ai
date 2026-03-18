"""
NexusOS Webhook System
Enables event-driven integrations with external services
"""
import os
import json
import logging
import requests
from threading import Thread
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class WebhookManager:
    """Manages webhook registrations and event dispatching"""
    
    def __init__(self, db=None):
        self.db = db
        self._webhooks: Dict[str, List[Dict]] = {}  # event_type -> list of webhook configs
        self._load_webhooks()
    
    def _load_webhooks(self):
        """Load webhooks from database"""
        if not self.db:
            return
        
        try:
            with self.db._get_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT event_type, url, secret, enabled FROM webhooks WHERE enabled = 1")
                for row in c.fetchall():
                    event_type = row[0]
                    webhook = {
                        'url': row[1],
                        'secret': row[2],
                        'enabled': bool(row[3])
                    }
                    if event_type not in self._webhooks:
                        self._webhooks[event_type] = []
                    self._webhooks[event_type].append(webhook)
        except Exception as e:
            logger.warning(f"Could not load webhooks: {e}")
    
    def register_webhook(self, event_type: str, url: str, secret: str = None, user_id: str = None) -> Dict:
        """Register a new webhook"""
        webhook_id = os.urandom(8).hex()
        
        webhook = {
            'id': webhook_id,
            'event_type': event_type,
            'url': url,
            'secret': secret or os.urandom(16).hex(),
            'user_id': user_id,
            'enabled': True
        }
        
        if event_type not in self._webhooks:
            self._webhooks[event_type] = []
        self._webhooks[event_type].append(webhook)
        
        # Persist to database
        if self.db:
            try:
                with self.db._get_conn() as conn:
                    c = conn.cursor()
                    c.execute("""
                        INSERT OR REPLACE INTO webhooks (id, user_id, event_type, url, secret, enabled, created_at)
                        VALUES (?, ?, ?, ?, ?, 1, datetime('now'))
                    """, (webhook_id, user_id, event_type, url, webhook['secret']))
            except Exception as e:
                logger.error(f"Failed to save webhook: {e}")
        
        logger.info(f"Registered webhook {webhook_id} for {event_type}")
        return webhook
    
    def unregister_webhook(self, webhook_id: str, user_id: str = None) -> bool:
        """Unregister a webhook"""
        for event_type, hooks in self._webhooks.items():
            for i, hook in enumerate(hooks):
                if hook.get('id') == webhook_id:
                    if user_id and hook.get('user_id') != user_id:
                        return False
                    hooks.pop(i)
                    
                    # Remove from database
                    if self.db:
                        try:
                            with self.db._get_conn() as conn:
                                c = conn.cursor()
                                c.execute("DELETE FROM webhooks WHERE id = ?", (webhook_id,))
                        except Exception as e:
                            logger.error(f"Failed to delete webhook: {e}")
                    
                    return True
        return False
    
    def list_webhooks(self, user_id: str = None) -> List[Dict]:
        """List registered webhooks"""
        result = []
        for event_type, hooks in self._webhooks.items():
            for hook in hooks:
                if user_id is None or hook.get('user_id') == user_id:
                    result.append({
                        'id': hook.get('id'),
                        'event_type': event_type,
                        'url': hook['url'],
                        'enabled': hook.get('enabled', True)
                    })
        return result
    
    def dispatch(self, event_type: str, payload: Dict[str, Any]):
        """Dispatch an event to all registered webhooks (async)"""
        webhooks = self._webhooks.get(event_type, [])
        
        if not webhooks:
            return
        
        for webhook in webhooks:
            if webhook.get('enabled', True):
                # Run async to not block
                Thread(target=self._send_webhook, args=(webhook, event_type, payload)).start()
    
    def _send_webhook(self, webhook: Dict, event_type: str, payload: Dict):
        """Send webhook payload to URL"""
        import hmac
        import hashlib
        
        try:
            # Add event metadata
            from datetime import datetime
            data = {
                'event': event_type,
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'data': payload
            }
            
            # Sign payload if secret is set
            headers = {'Content-Type': 'application/json'}
            if webhook.get('secret'):
                body = json.dumps(data)
                signature = hmac.new(
                    webhook['secret'].encode(),
                    body.encode(),
                    hashlib.sha256
                ).hexdigest()
                headers['X-NexusOS-Signature'] = f'sha256={signature}'
            
            response = requests.post(
                webhook['url'],
                json=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"Webhook delivered: {event_type} -> {webhook['url']}")
            else:
                logger.warning(f"Webhook failed: {event_type} -> {webhook['url']} (status {response.status_code})")
                
        except Exception as e:
            logger.error(f"Webhook error: {event_type} -> {webhook['url']}: {e}")


# Singleton instance
_webhook_manager: Optional[WebhookManager] = None

def get_webhook_manager(db=None) -> WebhookManager:
    """Get or create webhook manager"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager(db)
    return _webhook_manager
