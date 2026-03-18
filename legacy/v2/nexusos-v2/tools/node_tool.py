"""
Node Tool - Control paired devices (phone, laptop, etc)
Note: Requires OpenClaw nodes API to be available
"""
import os
import requests
from typing import Dict, List, Optional

class NodeTool:
    """Control paired devices via OpenClaw nodes API"""
    
    def __init__(self, gateway_url: str = None, api_token: str = None):
        self.gateway_url = gateway_url or os.getenv("GATEWAY_URL", "http://localhost:8080")
        self.api_token = api_token or os.getenv("GATEWAY_API_TOKEN")
        self.session = requests.Session()
        if self.api_token:
            self.session.headers["Authorization"] = f"Bearer {self.api_token}"
    
    # ========== DEVICE DISCOVERY ==========
    
    def list_nodes(self) -> Dict:
        """List all paired devices"""
        try:
            response = self.session.get(f"{self.gateway_url}/nodes", timeout=10)
            if response.status_code == 200:
                return {"success": True, "nodes": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_node(self, node_id: str) -> Dict:
        """Get device info"""
        try:
            response = self.session.get(f"{self.gateway_url}/nodes/{node_id}", timeout=10)
            if response.status_code == 200:
                return {"success": True, "node": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== CAMERA ==========
    
    def camera_snap(self, node_id: str, facing: str = "back") -> Dict:
        """Take photo with device camera"""
        try:
            response = self.session.post(
                f"{self.gateway_url}/nodes/{node_id}/camera/snap",
                json={"facing": facing},
                timeout=30
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "image": result.get("image"),
                    "path": result.get("path")
                }
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def camera_clip(self, node_id: str, duration: int = 3, facing: str = "back") -> Dict:
        """Record video clip"""
        try:
            response = self.session.post(
                f"{self.gateway_url}/nodes/{node_id}/camera/clip",
                json={"duration": duration, "facing": facing},
                timeout=duration + 10
            )
            if response.status_code == 200:
                result = response.json()
                return {"success": True, "video": result.get("video")}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== PHOTOS ==========
    
    def photos_latest(self, node_id: str, count: int = 5) -> Dict:
        """Get latest photos from device"""
        try:
            response = self.session.get(
                f"{self.gateway_url}/nodes/{node_id}/photos/latest",
                params={"count": count},
                timeout=15
            )
            if response.status_code == 200:
                return {"success": True, "photos": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== LOCATION ==========
    
    def location_get(self, node_id: str, accuracy: str = "balanced") -> Dict:
        """Get device location"""
        try:
            response = self.session.get(
                f"{self.gateway_url}/nodes/{node_id}/location",
                params={"accuracy": accuracy},
                timeout=15
            )
            if response.status_code == 200:
                return {"success": True, "location": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== NOTIFICATIONS ==========
    
    def notifications_list(self, node_id: str, limit: int = 20) -> Dict:
        """List recent notifications"""
        try:
            response = self.session.get(
                f"{self.gateway_url}/nodes/{node_id}/notifications",
                params={"limit": limit},
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "notifications": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def notifications_dismiss(self, node_id: str, notification_key: str) -> Dict:
        """Dismiss notification"""
        try:
            response = self.session.delete(
                f"{self.gateway_url}/nodes/{node_id}/notifications/{notification_key}",
                timeout=10
            )
            return {"success": response.status_code == 200, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== SCREEN ==========
    
    def screen_record(self, node_id: str, duration: int = 5) -> Dict:
        """Record screen"""
        try:
            response = self.session.post(
                f"{self.gateway_url}/nodes/{node_id}/screen/record",
                json={"duration": duration},
                timeout=duration + 10
            )
            if response.status_code == 200:
                return {"success": True, "video": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== COMMANDS ==========
    
    def run_command(self, node_id: str, command: List[str], cwd: str = None, timeout: int = 30) -> Dict:
        """Run shell command on device"""
        try:
            response = self.session.post(
                f"{self.gateway_url}/nodes/{node_id}/run",
                json={"command": command, "cwd": cwd, "timeout": timeout},
                timeout=timeout + 5
            )
            if response.status_code == 200:
                return {"success": True, "output": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ========== DEVICE STATUS ==========
    
    def device_status(self, node_id: str) -> Dict:
        """Get device battery, storage, etc"""
        try:
            response = self.session.get(f"{self.gateway_url}/nodes/{node_id}/device/status", timeout=10)
            if response.status_code == 200:
                return {"success": True, "status": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def device_info(self, node_id: str) -> Dict:
        """Get device info (model, OS, etc)"""
        try:
            response = self.session.get(f"{self.gateway_url}/nodes/{node_id}/device/info", timeout=10)
            if response.status_code == 200:
                return {"success": True, "info": response.json()}
            return {"success": False, "error": f"Status {response.status_code}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_node_tool = None

def get_node_tool(gateway_url: str = None, api_token: str = None) -> NodeTool:
    global _node_tool
    if _node_tool is None:
        _node_tool = NodeTool(gateway_url, api_token)
    return _node_tool