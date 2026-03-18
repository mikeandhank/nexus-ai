"""
NexusOS MCP Server - Model Context Protocol Implementation
"""

import json
from typing import Dict, List, Any

# Import expanded tools
try:
    from mcp_tools_expanded import MCP_TOOLS as EXPANDED_TOOLS
except ImportError:
    EXPANDED_TOOLS = []


class MCPTools:
    """MCP Tools capability."""
    
    def __init__(self, tool_engine):
        self.tool_engine = tool_engine
    
    def list(self) -> List[Dict]:
        # Use expanded tools if available, otherwise use basic set
        if EXPANDED_TOOLS:
            return [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            k: {"type": v["type"], "description": v.get("description", "")}
                            for k, v in t.get("parameters", {}).items()
                        },
                        "required": t.get("parameters", {}).get("required", [])
                    }
                }
                for t in EXPANDED_TOOLS
            ]
        
        # Fallback to basic tools
        return [
            {"name": "file_read", "description": "Read a file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "file_write", "description": "Write to a file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"name": "file_list", "description": "List directory contents", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
            {"name": "process_run", "description": "Run a shell command", "inputSchema": {"type": "object", "properties": {"command": {"type": "string"}, "timeout": {"type": "number"}}, "required": ["command"]}},
            {"name": "http_get", "description": "HTTP GET request", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
            {"name": "http_post", "description": "HTTP POST request", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}, "data": {"type": "object"}}}},
            {"name": "system_info", "description": "Get system info", "inputSchema": {"type": "object", "properties": {}}},
            {"name": "search_files", "description": "Search files by content", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}}, "required": ["query"]}},
        ]
    
    def call(self, name: str, arguments: Dict) -> Dict:
        # Try expanded tools first
        for tool in EXPANDED_TOOLS:
            if tool["name"] == name:
                # Execute the tool - simplified for now
                return {"result": f"Tool {name} called with {arguments}"}
        
        # Fallback to basic tool engine
        result = self.tool_engine.execute_tool(name, **arguments)
        return result.to_dict() if hasattr(result, 'to_dict') else {"result": str(result)}


class MCPResources:
    """MCP Resources capability."""
    
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
    
    def list(self) -> List[Dict]:
        return [
            {"uri": "nexus://user/me", "name": "Current User", "mimeType": "application/json"},
            {"uri": "nexus://memories/episodic", "name": "Episodic Memories", "mimeType": "application/json"},
            {"uri": "nexus://conversations", "name": "Recent Conversations", "mimeType": "application/json"},
        ]
    
    def read(self, uri: str) -> str:
        parts = uri.replace("nexus://", "").split("/")
        if not self.user_id:
            return json.dumps({"error": "Not authenticated"})
        
        if parts[0] == "memories" and len(parts) > 1:
            if parts[1] == "episodic":
                memories = self.db.get_episodic_memories(self.user_id)
                return json.dumps(memories[:10])
        elif parts[0] == "conversations":
            convs = self.db.get_conversations(self.user_id)
            return json.dumps(convs[:10])
        
        return json.dumps({"error": "Resource not found"})


class MCPServer:
    """Main MCP Server."""
    
    def __init__(self, db, tool_engine, user_id=None):
        self.db = db
        self.tool_engine = tool_engine
        self.user_id = user_id
        self.tools = MCPTools(tool_engine)
        self.resources = MCPResources(db, user_id)
        self.server_info = {
            "name": "NexusOS MCP Server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}, "resources": {}}
        }
    
    def handle_message(self, message: Dict) -> Dict:
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        try:
            if method == "initialize":
                result = self.server_info
            elif method == "tools/list":
                result = {"tools": self.tools.list()}
            elif method == "tools/call":
                result = self.tools.call(params.get("name"), params.get("arguments", {}))
            elif method == "resources/list":
                result = {"resources": self.resources.list()}
            elif method == "resources/read":
                result = {"contents": [{"uri": params.get("uri"), "mimeType": "application/json", "text": self.resources.read(params.get("uri"))}]}
            else:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}


def create_mcp_server(db, tool_engine, user_id=None):
    return MCPServer(db, tool_engine, user_id)
