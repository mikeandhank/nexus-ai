"""
vLLM Integration Module
=======================
Support for vLLM as alternative high-performance LLM runtime
"""
import os
import requests
from typing import Dict, List, Optional


class vLLMManager:
    """
    Manage vLLM inference server
    
    vLLM provides:
    - PagedAttention for memory efficiency
    - Continuous batching
    - Higher throughput than Ollama
    """
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get('VLLM_BASE_URL', 'http://localhost:8000')
        self.api_key = os.environ.get('VLLM_API_KEY')
    
    def health(self) -> Dict:
        """Check vLLM health"""
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=5)
            return {"status": "healthy" if resp.status_code == 200 else "unhealthy"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def list_models(self) -> List[str]:
        """List available models"""
        try:
            resp = requests.get(f"{self.base_url}/v1/models", timeout=5)
            if resp.status_code == 200:
                return [m['id'] for m in resp.json()['data']]
            return []
        except Exception:
            return []
    
    def generate(self, prompt: str, model: str = None, 
                 max_tokens: int = 512, temperature: float = 0.7,
                 stream: bool = False) -> Dict:
        """
        Generate text with vLLM
        
        Example:
            result = vllm.generate("Hello, I am", model="meta-llama/Llama-2-7b-chat-hf")
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": model or "default",
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }
        
        try:
            resp = requests.post(
                f"{self.base_url}/v1/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "text": data['choices'][0]['text'],
                    "tokens": data['usage']['completion_tokens'],
                    "model": data['model']
                }
            
            return {"success": False, "error": resp.text}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def chat_complete(self, messages: List[Dict], model: str = None,
                      temperature: float = 0.7) -> Dict:
        """
        Chat completion (OpenAI-compatible)
        
        Example:
            messages = [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"}
            ]
            result = vllm.chat_complete(messages)
        """
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        payload = {
            "model": model or "default",
            "messages": messages,
            "temperature": temperature
        }
        
        try:
            resp = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "success": True,
                    "message": data['choices'][0]['message']['content'],
                    "tokens": data['usage']['completion_tokens']
                }
            
            return {"success": False, "error": resp.text}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_server_info(self) -> Dict:
        """Get vLLM server information"""
        try:
            resp = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return {"models": self.list_models()} if resp.status_code == 200 else {}
        except Exception:
            return {}


# vLLM Docker Compose snippet
VLLM_COMPOSE = """
# vLLM High-Performance Inference
# Run with: docker compose -f docker-compose.vllm.yml up -d

services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: nexusos-vllm
    ports:
      - "8000:8000"
    environment:
      - HF_TOKEN=${HF_TOKEN}
    volumes:
      - ./models:/models
    command: >
      --model meta-llama/Llama-2-7b-chat-hf
      --tensor-parallel-size 1
      --dtype half
      --port 8000
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
"""


def create_vllm_compose():
    """Create vLLM docker-compose file"""
    with open('/data/.openclaw/workspace/nexusos-v2/docker-compose.vllm.yml', 'w') as f:
        f.write(VLLM_COMPOSE)


# Singleton
_vllm_manager = None

def get_vllm_manager() -> vLLMManager:
    global _vllm_manager
    if _vllm_manager is None:
        _vllm_manager = vLLMManager()
    return _vllm_manager