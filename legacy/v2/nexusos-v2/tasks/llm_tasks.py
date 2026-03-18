"""
LLM Tasks - Async inference, streaming, batch processing
"""
from tasks.celery_app import app
import asyncio
import json

@app.task(bind=True)
def chat_async(self, user_id, message, conversation_id=None, provider='ollama', model='phi3'):
    """Process chat request asynchronously"""
    from llm_integration import LLMManager
    
    llm = LLMManager()
    response = llm.chat(
        user_id=user_id,
        message=message,
        conversation_id=conversation_id,
        provider=provider,
        model=model
    )
    
    return {
        'response': response.get('response'),
        'conversation_id': response.get('conversation_id'),
        'tokens': response.get('tokens', 0),
        'cost': response.get('cost', 0)
    }

@app.task
def batch_chat(user_id, messages):
    """Process multiple chat messages in batch"""
    from llm_integration import LLMManager
    
    llm = LLMManager()
    results = []
    
    for msg in messages:
        resp = llm.chat(user_id=user_id, message=msg)
        results.append(resp)
    
    return results

@app.task
def stream_chat(user_id, message):
    """Streaming chat - returns generator"""
    from llm_integration import LLMManager
    
    llm = LLMManager()
    return llm.chat_stream(user_id=user_id, message=message)
