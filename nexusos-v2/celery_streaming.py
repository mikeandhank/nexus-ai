"""
Celery Streaming Module
=======================
Redis pub/sub for streaming responses via Celery
"""
import os
import json
import redis
from typing import AsyncGenerator, Dict
from celery import Celery


# Celery app
celery_app = Celery(
    'nexusos',
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)


# Redis pub/sub for streaming
class StreamManager:
    """Manage streaming responses via Redis pub/sub"""
    
    def __init__(self):
        self.redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
        self.redis = redis.from_url(self.redis_url)
        self.pubsub = None
    
    def publish_chunk(self, channel: str, chunk: dict):
        """Publish a chunk to a channel"""
        self.redis.publish(channel, json.dumps(chunk))
    
    def subscribe(self, channel: str):
        """Subscribe to a channel for streaming"""
        self.pubsub = self.redis.pubsub()
        self.pubsub.subscribe(channel)
        return self.pubsub
    
    def unsubscribe(self, channel: str):
        """Unsubscribe from channel"""
        if self.pubsub:
            self.pubsub.unsubscribe(channel)


# Celery task for streaming chat
@celery_app.task(bind=True)
def stream_chat_task(self, message: str, agent_id: str = None):
    """Process chat and stream response via Redis"""
    channel = f"stream:{self.request.id}"
    
    manager = StreamManager()
    
    # Send initial status
    manager.publish_chunk(channel, {
        "type": "start",
        "task_id": self.request.id
    })
    
    # Process message (placeholder - integrate with LLM)
    response = f"Response to: {message}"
    words = response.split()
    
    for i, word in enumerate(words):
        manager.publish_chunk(channel, {
            "type": "chunk",
            "content": word,
            "index": i,
            "total": len(words)
        })
    
    # Send done
    manager.publish_chunk(channel, {
        "type": "done",
        "task_id": self.request.id
    })
    
    return {"status": "complete", "response": response}


# FastAPI endpoint for streaming
async def stream_chat(message: str, agent_id: str = None) -> AsyncGenerator[str, None]:
    """Stream chat response using Celery + Redis pub/sub"""
    # Submit task
    task = stream_chat_task.delay(message, agent_id)
    channel = f"stream:{task.id}"
    
    manager = StreamManager()
    pubsub = manager.subscribe(channel)
    
    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                
                if data['type'] == 'chunk':
                    yield f"data: {data['content']}\n\n"
                elif data['type'] == 'done':
                    yield "data: [DONE]\n\n"
                    break
    finally:
        manager.unsubscribe(channel)


# Example usage in FastAPI:
# @app.post("/api/chat/stream")
# async def chat_stream(request: Request):
#     body = await request.json()
#     return StreamingResponse(
#         stream_chat(body.get("message", ""), body.get("agent_id")),
#         media_type="text/event-stream"
#     )