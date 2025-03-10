"""
Webhook notifications for Infoblox Mock Server
"""

import logging
import json
import threading
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookManager:
    """Manager for webhook notifications"""
    
    def __init__(self):
        """Initialize the webhook manager"""
        self.webhooks = {}
    
    def register_webhook(self, event_type, url, headers=None):
        """Register a webhook for an event type"""
        if event_type not in self.webhooks:
            self.webhooks[event_type] = []
        
        # Add webhook if it doesn't already exist
        webhook = {
            'url': url,
            'headers': headers or {},
            'created': datetime.now().isoformat()
        }
        
        for existing in self.webhooks[event_type]:
            if existing['url'] == url:
                # Update headers if webhook already exists
                existing['headers'] = headers or {}
                return True
        
        # Add new webhook
        self.webhooks[event_type].append(webhook)
        logger.info(f"Registered webhook for {event_type}: {url}")
        return True
    
    def unregister_webhook(self, event_type, url):
        """Unregister a webhook"""
        if event_type not in self.webhooks:
            return False
        
        # Remove webhook if it exists
        initial_count = len(self.webhooks[event_type])
        self.webhooks[event_type] = [w for w in self.webhooks[event_type] if w['url'] != url]
        
        # Check if any were removed
        if len(self.webhooks[event_type]) < initial_count:
            logger.info(f"Unregistered webhook for {event_type}: {url}")
            return True
        
        return False
    
    def notify_webhook(self, event_type, data):
        """Send a webhook notification for an event"""
        if event_type not in self.webhooks:
            return
        
        # Add timestamp to data
        enriched_data = {
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        # Send notifications asynchronously
        def send_notification(webhook, payload):
            try:
                response = requests.post(
                    webhook['url'],
                    json=payload,
                    headers=webhook['headers'],
                    timeout=5
                )
                logger.info(f"Webhook notification sent to {webhook['url']}, status: {response.status_code}")
            except Exception as e:
                logger.error(f"Error sending webhook notification to {webhook['url']}: {str(e)}")
        
        # Send to all registered webhooks for this event type
        for webhook in self.webhooks[event_type]:
            thread = threading.Thread(
                target=send_notification,
                args=(webhook, enriched_data)
            )
            thread.daemon = True
            thread.start()
    
    def get_webhooks(self, event_type=None):
        """Get all registered webhooks"""
        if event_type:
            return self.webhooks.get(event_type, [])
        
        # Return all webhooks grouped by event type
        return self.webhooks

# Create a global instance
webhook_manager = WebhookManager()