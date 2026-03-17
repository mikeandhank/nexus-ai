"""
Streaming Module
================
WebSocket and SSE support for real-time agent responses
COMPETITIVE GAP: Streaming was identified as critical missing feature
"""
import json
import asyncio
import uuid
from typing import AsyncGenerator, Dict, Callable, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


class StreamFormat(Enum):
    """Streaming response format"""
    SSE = "sse"  # Server-Sent Events
    WS = "ws"    # WebSocket


@dataclass
class StreamChunk:
    """A chunk of streaming data"""
    chunk_id: str
    content: str
    delta: str  # Incremental content
    done: bool
    timestamp: datetime


class StreamingGenerator:
    """
    Base class for streaming responses
    """
    
    def __init__(self):
        self.chunks = []
    
    async def generate(self, data: str, chunk_size: int = 10) -> AsyncGenerator[StreamChunk, None]:
        """Generate chunks from data"""
        chunk_id = str(uuid.uuid4())[:8]
        
        # Split into words
        words = data.split()
        
        for i, word in enumerate(words):
            is_last = i == len(words) - 1
            
            chunk = StreamChunk(
                chunk_id=chunk_id,
                content=word,
                delta=word + (" " if not is_last else ""),
                done=is_last,
                timestamp=datetime.utcnow()
            )
            
            self.chunks.append(chunk)
            yield chunk
            
            # Small delay to simulate streaming
            await asyncio.sleep(0.02)


class SSEStreamer:
    """
    Server-Sent Events streamer
    """
    
    @staticmethod
    def format_sse(event: str, data: str) -> str:
        """Format SSE message"""
        return f"event: {event}\ndata: {data}\n\n"
    
    @staticmethod
    def format_sse_json(event: str, data: dict) -> str:
        """Format SSE JSON message"""
        return SSEStreamer.format_sse(event, json.dumps(data))
    
    async def stream_response(self, generator: StreamingGenerator, 
                             data: str) -> AsyncGenerator[str, None]:
        """Stream response as SSE"""
        async for chunk in generator.generate(data):
            if chunk.delta:
                yield self.format_sse_json("chunk", {
                    "content": chunk.delta,
                    "done": chunk.done
                })
            
            if chunk.done:
                yield self.format_sse_json("done", {"chunk_id": chunk.chunk_id})


class WebSocketHandler:
    """
    WebSocket handler for real-time communication
    """
    
    def __init__(self):
        self.active_connections: Dict[str, any] = {}
    
    async def handle_connection(self, websocket, client_id: str):
        """Handle WebSocket connection"""
        self.active_connections[client_id] = websocket
        
        try:
            await websocket.send(json.dumps({
                "type": "connected",
                "client_id": client_id
            }))
            
            # Handle incoming messages
            async for message in websocket:
                await self.handle_message(client_id, message)
                
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            del self.active_connections[client_id]
    
    async def handle_message(self, client_id: str, message: str):
        """Handle incoming WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "ping":
                await self.send_to(client_id, {"type": "pong"})
            elif msg_type == "chat":
                # Process chat and stream response
                await self.stream_chat(client_id, data.get("message", ""))
                
        except json.JSONDecodeError:
            await self.send_to(client_id, {
                "type": "error",
                "message": "Invalid JSON"
            })
    
    async def stream_chat(self, client_id: str, message: str):
        """Stream chat response"""
        # This would integrate with your LLM
        response = f"Echo: {message}"  # Placeholder
        
        generator = StreamingGenerator()
        
        async for chunk in generator.generate(response):
            await self.send_to(client_id, {
                "type": "chunk",
                "content": chunk.delta,
                "done": chunk.done
            })
    
    async def send_to(self, client_id: str, data: dict):
        """Send message to specific client"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send(json.dumps(data))
    
    async def broadcast(self, data: dict):
        """Broadcast to all connected clients"""
        for client_id in self.active_connections:
            await self.send_to(client_id, data)


# Streaming chat endpoint helper
async def stream_chat_response(message: str, llm_callback: Callable) -> AsyncGenerator[Dict, None]:
    """
    Generate streaming chat response
    
    Usage:
        async for chunk in stream_chat_response("Hello", my_llm):
            yield chunk
    """
    chunk_id = str(uuid.uuid4())[:8]
    full_response = ""
    
    # Get response from LLM (this is a placeholder)
    # In production, this would call your LLM integration
    async for token in llm_callback(message):
        full_response += token
        
        yield {
            "chunk_id": chunk_id,
            "content": token,
            "delta": token,
            "done": False,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # Final chunk
    yield {
        "chunk_id": chunk_id,
        "content": "",
        "delta": "",
        "done": True,
        "timestamp": datetime.utcnow().isoformat(),
        "full_response": full_response
    }


# Singleton
_ws_handler = None

def get_websocket_handler() -> WebSocketHandler:
    global _ws_handler
    if _ws_handler is None:
        _ws_handler = WebSocketHandler()
    return _ws_handler