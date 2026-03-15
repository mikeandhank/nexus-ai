"""
NexusOS MCP Server - Model Context Protocol Implementation
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import get_db
from tool_engine import get_tool_engine


class MCPTools:
    """MCP Tools capability."""
    
    def __init__(self, server):
        self.server = server
    
    def list(self) -> List[Dict]:
        """List all available tools."""
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
        """Call a tool."""
        result = self.server.tool_engine.execute_tool(name, **arguments)
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        return {"result": str(result)}


class MCPResources:
    """MCP Resources capability."""
    
    def __init__(self, server):
        self.server = server
    
    def list(self) -> List[Dict]:
        """List available resources."""
        return [
            {"uri": "nexus://user/me", "name": "Current User", "mimeType": "application/json"},
            {"uri": "nexus://memories/episodic", "name": "Episodic Memories", "mimeType": "application/json"},
            {"uri": "nexus://memories/semantic", "name": "Semantic Memories", "mimeType": "application/json"},
            {"uri": "nexus://conversations", "name": "Recent Conversations", "mimeType": "application/json"},
            {"uri": "nexus://agents", "name": "Available Agents", "mimeType": "application/json"},
        ]
    
    def read(self, uri: str) -> str:
        """Read a resource."""
        parts = uri.replace("nexus://", "").split("/")
        
        if parts[0] == "memories" and len(parts) > 1:
            memory_type = parts[1]
            if memory_type == "episodic" and self.server.user_id:
                memories = self.server.db.get_episodic_memories(self.server.user_id)
                return json.dumps(memories[:10])
        
        elif parts[0] == "conversations" and self.server.user_id:
            convs = self.server.db.get_conversations(self.server.user_id)
            return json.dumps(convs[:10])
        
        elif parts[0] == "agents" and self.server.user_id:
            try:
                from agent_pool import get_agent_pool
                pool = get_agent_pool()
                agents = pool.get_agents(self.server.user_id)
                return json.dumps([a.to_dict() for a in agents])
            except:
                return json.dumps([])
        
        return json.dumps({"error": "Resource not found"})


class MCPServer:
    """Main MCP Server for NexusOS."""
    
    def __init__(self, user_id: str = None, db_path: str = None, workspace_dir: str = None):
        self.user_id = user_id
        self.db = get_db(db_path)
        self.tool_engine = get_tool_engine(workspace_dir)
        self.tools = MCPTools(self)
        self.resources = MCPResources(self)
        self.server_info = {
            "name": "NexusOS MCP Server",
            "version": "1.0.0",
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True},
            }
        }
    
    def handle_message(self, message: Dict) -> Dict:
        """Handle an MCP message."""
        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params", {})
        
        try:
            if method == "initialize":
                result = self.server_info
            elif method == "tools/list":
                result = {"tools": self.tools.list()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = self.tools.call(tool_name, arguments)
            elif method == "resources/list":
                result = {"resources": self.resources.list()}
            elif method == "resources/read":
                uri = params.get("uri")
                contents = [{"uri": uri, "mimeType": "application/json", "text": self.resources.read(uri)}]
                result = {"contents": contents}
            else:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}
            
            return {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except Exception as e:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}


# Verify syntax
import py_compile
py_compile.compile('/data/.openclaw/workspace/nexusos-v2/mcp_server.py', doraise=True)
print("mcp_server.py: OK")
