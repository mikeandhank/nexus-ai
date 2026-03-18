"""
WebSocket Streaming Support
============================
Real-time chat responses via WebSocket.
"""
from flask import Flask, request
from flask_sock import Sock
from threading import Thread
import json
import queue

app = Flask(__name__)
sock = Sock(app)

# Store active connections per session
connections = {}


class StreamManager:
    """Manage streaming responses."""
    
    def __init__(self):
        self.active_streams = {}
    
    def create_stream(self, session_id: str):
        """Create a new stream for a session."""
        q = queue.Queue()
        self.active_streams[session_id] = {
            'queue': q,
            'complete': False
        }
        return q
    
    def send_chunk(self, session_id: str, chunk: str):
        """Send a chunk to a stream."""
        if session_id in self.active_streams:
            self.active_streams[session_id]['queue'].put(chunk)
    
    def complete(self, session_id: str):
        """Mark stream as complete."""
        if session_id in self.active_streams:
            self.active_streams[session_id]['complete'] = True
            self.active_streams[session_id]['queue'].put(None)  # Signal end
    
    def close(self, session_id: str):
        """Close a stream."""
        if session_id in self.active_streams:
            del self.active_streams[session_id]


stream_manager = StreamManager()


@sock.route('/api/ws/chat')
def chat_websocket(ws):
    """WebSocket endpoint for streaming chat."""
    session_id = None
    
    try:
        # Authenticate
        auth_data = ws.receive()
        if auth_data:
            auth = json.loads(auth_data)
            session_id = auth.get('session_id')
            
            if not session_id:
                ws.send(json.dumps({'error': 'No session_id'}))
                return
        
        # Create stream
        q = stream_manager.create_stream(session_id)
        ws.send(json.dumps({'status': 'connected', 'session_id': session_id}))
        
        # Send chunks as they arrive
        while True:
            chunk = q.get()
            if chunk is None:
                ws.send(json.dumps({'done': True}))
                break
            ws.send(json.dumps({'chunk': chunk}))
            
    except Exception as e:
        pass
    finally:
        if session_id:
            stream_manager.close(session_id)


def stream_response(session_id: str, generator):
    """Stream a response to a WebSocket client."""
    for chunk in generator:
        stream_manager.send_chunk(session_id, chunk)
    stream_manager.complete(session_id)


# Example usage with chat endpoint
def create_streaming_response(prompt: str, model: str = 'phi3'):
    """Generate streaming response."""
    import requests
    ollama_url = "http://localhost:11434/api/generate"
    
    response = requests.post(
        ollama_url,
        json={'model': model, 'prompt': prompt, 'stream': True},
        stream=True
    )
    
    for line in response.iter_lines():
        if line:
            data = json.loads(line)
            yield data.get('response', '')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)