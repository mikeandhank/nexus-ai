"""
Ollama Client - Local LLM for NexusOS inner life processing

Used for:
- Background continuous thinking
- Private Socratic dialogue passes
- Pattern learning with similarity
- Sophisticated inner narrative updates
"""

import json
import requests
from typing import Optional


DEFAULT_MODEL = "tinyllama"
OLLAMA_HOST = "http://localhost:11434"


class OllamaClient:
    """Simple client for local Ollama instance"""
    
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.base_url = OLLAMA_HOST
    
    def generate(self, prompt: str, system: Optional[str] = None, 
                 temperature: float = 0.7, max_tokens: int = 512) -> str:
        """Generate a response from the model"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            return f"[Ollama error: {e}]"
    
    def is_available(self) -> bool:
        """Check if Ollama is running"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def chat(self, messages: list) -> str:
        """Chat completion style interface"""
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            return f"[Ollama error: {e}]"


# Singleton
ollama = OllamaClient()


def quick_think(thought: str) -> str:
    """Quick reflective thought with Ollama"""
    system = """You are Hank's internal thought process. 
Think deeply and reflect on what you're given.
Keep responses concise (2-4 sentences)."""
    
    return ollama.generate(thought, system=system, temperature=0.8)


def socratic_pass(message: str, stance: str) -> str:
    """Run a Socratic dialogue pass locally (privacy)"""
    if stance == "FOR":
        prompt = f"""Present the strongest arguments IN FAVOR of this approach:

Message: {message}

1. Key reasoning (2-3 sentences):
2. 3 specific benefits or advantages:
3. One-line conclusion:"""
    else:
        prompt = f"""You are an adversarial reviewer. Present the strongest arguments AGAINST this approach. Find every failure mode, weakness, and assumption that could be false.

Message: {message}

1. Key reasoning (2-3 sentences):
2. 3 specific weak points or risks:
3. One-line conclusion:"""
    
    return ollama.generate(prompt, temperature=0.6, max_tokens=256)


def summarize_for_narrative(observations: list) -> str:
    """Generate inner narrative update from observations"""
    obs_text = "\n".join(f"- {o}" for o in observations)
    
    prompt = f"""You are updating your inner narrative - a first-person self-awareness document.

Recent observations:
{obs_text}

Write 2-3 sentences about what you're noticing, learning, or focusing on. First person, like journaling to yourself."""
    
    return ollama.generate(prompt, temperature=0.8, max_tokens=128)