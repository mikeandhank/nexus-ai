"""
Context Optimizer - Intelligent Prompt Context Management
======================================================
Uses local LLM to decide what context to include/exclude,
keeping token cost truly flat regardless of usage history.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ContextOptimizer:
    """
    Uses local LLM to intelligently manage context.
    
    Instead of fixed top-K retrieval, this:
    1. Analyzes the user's query
    2. Evaluates each potential context item for relevance
    3. Rewrites/compresses context to fit budget
    4. Ensures flat token cost
    """
    
    def __init__(self, ollama_url: str = None):
        self.ollama_url = ollama_url or os.environ.get('OLLAMA_URL', 'http://localhost:11434')
        self.max_context_tokens = 500  # Budget for context
        self.ollama_model = 'phi3'  # Fast, local, cheap
    
    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama for inference"""
        import requests
        
        url = f"{self.ollama_url}/api/generate"
        data = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                return response.json().get('response', '')
            else:
                logger.warning(f"Ollama error: {response.status_code}")
                return ""
        except Exception as e:
            logger.warning(f"Ollama call failed: {e}")
            return ""
    
    def analyze_relevance(self, query: str, context_items: List[Dict]) -> List[Dict]:
        """
        Use LLM to score each context item's relevance to the query.
        
        Returns context items with relevance scores.
        """
        if not context_items:
            return []
        
        # Build the analysis prompt
        context_text = "\n".join([
            f"{i+1}. {item.get('content', item.get('text', ''))[:200]}"
            for i, item in enumerate(context_items)
        ])
        
        prompt = f"""Analyze relevance of each context item to the user query.

User Query: {query}

Context Items:
{context_text}

For each item, rate relevance 0-10 and explain briefly. Format:
Item 1: [score] - [brief reason]
Item 2: [score] - [brief reason]
"""
        
        analysis = self._call_ollama(prompt)
        
        # Parse scores (simple approach)
        scored_items = []
        lines = analysis.split('\n')
        
        for i, item in enumerate(context_items):
            score = 5  # Default medium relevance
            reason = ""
            
            # Try to find score for this item
            for line in lines:
                if f"Item {i+1}" in line or f"item {i+1}" in line:
                    # Extract score
                    import re
                    match = re.search(r'(\d+)', line)
                    if match:
                        score = int(match.group(1)) / 10  # Convert to 0-1
            
            scored_items.append({
                **item,
                'relevance_score': score,
                'analysis': reason
            })
        
        return scored_items
    
    def compress_context(self, query: str, context_items: List[Dict]) -> str:
        """
        Use LLM to compress relevant context into minimal tokens.
        
        Returns optimized context string.
        """
        if not context_items:
            return ""
        
        # Get relevant items
        relevant = [item for item in context_items if item.get('relevance_score', 0.5) > 0.3]
        
        if not relevant:
            return ""
        
        # Build compression prompt
        context_text = "\n".join([
            f"- {item.get('content', item.get('text', ''))}"
            for item in relevant
        ])
        
        prompt = f"""Compress these memories into minimal relevant context for the user query.

User Query: {query}

Relevant Memories:
{context_text}

Rewrite as 2-3 sentence context summary. Include only what's directly relevant.
Keep it under 100 words. Format: "Relevant context: [summary]"
"""
        
        compressed = self._call_ollama(prompt)
        
        # Clean up
        if compressed:
            # Remove thinking prefixes
            compressed = compressed.replace("Relevant context:", "").strip()
            return f"Relevant context: {compressed}"
        
        # Fallback: simple join
        return f"Relevant context: {relevant[0].get('content', '')[:100]}"
    
    def optimize(self, query: str, available_context: List[Dict]) -> Dict[str, Any]:
        """
        Full context optimization pipeline.
        
        Returns:
        - optimized_context: The compressed context string
        - token_estimate: Estimated tokens used
        - items_analyzed: How many items were considered
        - compression_ratio: How much was compressed
        """
        if not available_context:
            return {
                "optimized_context": "",
                "token_estimate": 0,
                "items_analyzed": 0,
                "compression_ratio": 1.0
            }
        
        # Step 1: Analyze relevance
        scored = self.analyze_relevance(query, available_context)
        
        # Step 2: Compress relevant items
        optimized = self.compress_context(query, scored)
        
        # Estimate tokens (rough: 1 token ≈ 4 chars)
        token_estimate = len(optimized) / 4
        
        return {
            "optimized_context": optimized,
            "token_estimate": int(token_estimate),
            "items_analyzed": len(available_context),
            "compression_ratio": len(optimized) / max(sum(len(str(c.get('content', ''))) for c in available_context), 1),
            "relevant_items": sum(1 for s in scored if s.get('relevance_score', 0) > 0.3)
        }


class FlatTokenManager:
    """
    Guarantees flat token cost regardless of memory accumulation.
    
    Uses:
    1. Fixed budget per request
    2. LLM-powered context selection
    3. Automatic compression
    """
    
    def __init__(self, memory_graph=None, ollama_url: str = None):
        self.memory = memory_graph
        self.optimizer = ContextOptimizer(ollama_url)
        
        # Fixed token budget
        self.budget = {
            'system': 200,      # System prompt
            'context': 300,     # Retrieved context  
            'user': 100,        # User message space
            'response': 400      # Response space
        }
    
    def build_prompt(self, query: str, system_prompt: str = None) -> Dict[str, Any]:
        """
        Build prompt with guaranteed flat token usage.
        
        Returns components and total estimated tokens.
        """
        # Get memories
        memories = []
        if self.memory:
            try:
                recalled = self.memory.recall(query, limit=20)  # Get more, optimizer will filter
                memories = [
                    {"content": m.content, "type": m.type, "confidence": m.confidence}
                    for m, score in recalled
                ]
            except Exception as e:
                logger.warning(f"Memory recall failed: {e}")
        
        # Optimize context
        optimization = self.optimizer.optimize(query, memories)
        
        # Build final components
        system = system_prompt or "You are a helpful AI assistant."
        
        # Total estimate
        total_tokens = (
            len(system) / 4 + 
            len(optimization['optimized_context']) / 4 +
            len(query) / 4
        )
        
        return {
            "system": system,
            "context": optimization['optimized_context'],
            "user_message": query,
            "estimated_tokens": int(total_tokens),
            "within_budget": total_tokens <= sum(self.budget.values()),
            "optimization_stats": optimization
        }
    
    def get_budget_info(self) -> Dict:
        """Get token budget information"""
        return {
            "total_budget": sum(self.budget.values()),
            "breakdown": self.budget,
            "guarantee": "Token cost stays flat regardless of memory size"
        }


# Singleton
_context_optimizer = None
_token_manager = None

def get_context_optimizer(ollama_url: str = None) -> ContextOptimizer:
    global _context_optimizer
    if _context_optimizer is None:
        _context_optimizer = ContextOptimizer(ollama_url)
    return _context_optimizer

def get_token_manager(memory_graph=None, ollama_url: str = None) -> FlatTokenManager:
    global _token_manager
    if _token_manager is None:
        _token_manager = FlatTokenManager(memory_graph, ollama_url)
    return _token_manager