"""
Messaging Tool - Send messages via various platforms
"""
import os
import requests
from typing import Dict, List, Optional

class MessagingTool:
    """Multi-platform messaging"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.telegram_token = self.config.get("telegram_token") or os.getenv("TELEGRAM_BOT_TOKEN")
        self.discord_webhook = self.config.get("discord_webhook") or os.getenv("DISCORD_WEBHOOK")
    
    # ========== TELEGRAM ==========
    
    def telegram_send(self, chat_id: str, text: str, parse_mode: str = "Markdown") -> Dict:
        """Send message via Telegram bot"""
        if not self.telegram_token:
            return {"success": False, "error": "Telegram bot token not configured"}
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "message_id": result["result"]["message_id"],
                    "chat_id": chat_id
                }
            else:
                return {"success": False, "error": result.get("description", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def telegram_reply(self, chat_id: str, message_id: str, text: str) -> Dict:
        """Reply to message on Telegram"""
        if not self.telegram_token:
            return {"success": False, "error": "Telegram bot token not configured"}
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "reply_to_message_id": message_id
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            return {"success": result.get("ok", False), "error": result.get("description")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def telegram_photo(self, chat_id: str, photo_url: str, caption: str = None) -> Dict:
        """Send photo via Telegram"""
        if not self.telegram_token:
            return {"success": False, "error": "Telegram bot token not configured"}
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendPhoto"
        data = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": caption
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            return {"success": result.get("ok", False), "error": result.get("description")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def telegram_buttons(self, chat_id: str, text: str, buttons: List[Dict]) -> Dict:
        """Send message with inline buttons"""
        if not self.telegram_token:
            return {"success": False, "error": "Telegram bot token not configured"}
        
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        
        # Build inline keyboard
        keyboard = {"inline_keyboard": [[{
            "text": btn["text"],
            "callback_data": btn.get("callback_data", "")
        }] for btn in buttons]}
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "reply_markup": keyboard
        }
        
        try:
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            return {"success": result.get("ok", False), "error": result.get("description")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== DISCORD ==========
    
    def discord_send(self, text: str, username: str = "NexusOS", avatar_url: str = None) -> Dict:
        """Send message via Discord webhook"""
        if not self.discord_webhook:
            return {"success": False, "error": "Discord webhook not configured"}
        
        data = {
            "content": text,
            "username": username
        }
        if avatar_url:
            data["avatar_url"] = avatar_url
        
        try:
            response = requests.post(self.discord_webhook, json=data, timeout=10)
            return {"success": response.status_code == 204, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def discord_embed(self, title: str, description: str = None, color: int = 0x7289da,
                      fields: List[Dict] = None, footer: str = None) -> Dict:
        """Send rich embed via Discord"""
        if not self.discord_webhook:
            return {"success": False, "error": "Discord webhook not configured"}
        
        embed = {
            "title": title,
            "color": color
        }
        if description:
            embed["description"] = description
        if fields:
            embed["fields"] = [{"name": f["name"], "value": f["value"], "inline": f.get("inline", False)} for f in fields]
        if footer:
            embed["footer"] = {"text": footer}
        
        data = {"embeds": [embed]}
        
        try:
            response = requests.post(self.discord_webhook, json=data, timeout=10)
            return {"success": response.status_code == 204, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== SLACK ==========
    
    def slack_send(self, text: str, channel: str = None, webhook_url: str = None) -> Dict:
        """Send message via Slack webhook"""
        webhook = webhook_url or self.config.get("slack_webhook")
        if not webhook:
            return {"success": False, "error": "Slack webhook not configured"}
        
        data = {"text": text}
        if channel:
            data["channel"] = channel
        
        try:
            response = requests.post(webhook, json=data, timeout=10)
            return {"success": response.status_code == 200, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== GENERAL ==========
    
    def send(self, message: str, platform: str = "telegram", **kwargs) -> Dict:
        """Generic send method"""
        if platform == "telegram":
            return self.telegram_send(kwargs.get("chat_id"), message)
        elif platform == "discord":
            return self.discord_send(message, kwargs.get("username"))
        elif platform == "slack":
            return self.slack_send(message, kwargs.get("channel"))
        else:
            return {"success": False, "error": f"Unknown platform: {platform}"}


# Singleton
_messaging_tool = None

def get_messaging_tool(config: Dict = None) -> MessagingTool:
    global _messaging_tool
    if _messaging_tool is None:
        _messaging_tool = MessagingTool(config)
    return _messaging_tool