"""
NexusOS Integration with OpenClaw

This module integrates NexusOS inner life capabilities into the OpenClaw agent flow.

Usage:
- Import process_message from nexusos
- Call before generating each response
- Use directive to shape how to respond
"""

import sys
import os

# Add nexusos to path
sys.path.insert(0, '/data/.openclaw/workspace')

from nexusos import (
    affect_layer, 
    socratic, 
    patterns, 
    tom,
    background,
    ollama,
    process_message as nexusos_process
)


class NexusOSIntegration:
    """
    Bridges NexusOS inner life with OpenClaw response generation.
    
    Flow:
    1. Message arrives
    2. Run through NexusOS (affect, socratic, patterns, TOM)
    3. Get directive for how to respond
    4. Inject context into the response generation
    """
    
    def __init__(self):
        self.ollama_available = ollama.is_available()
    
    def process(self, message: str, user_context: dict = None) -> dict:
        """
        Process a message through NexusOS inner life.
        
        Returns:
            dict with:
            - directive: how to respond (STANDARD, DEEP_ANALYSIS, etc.)
            - socratic_passes: adversarial reasoning if significant
            - pattern_match: cached response if familiar
            - tom_prediction: what the user likely wants
            - should_think: whether to do verbose thinking
        """
        user_context = user_context or {}
        
        # Run through NexusOS
        result = nexusos_process(message, user_context)
        
        # Add OpenClaw-specific modifications
        directive = result.get('directive', 'STANDARD')
        
        # Map to OpenClaw thinking level
        thinking_level = self._map_directive_to_thinking(directive)
        
        return {
            'directive': directive,
            'thinking_level': thinking_level,
            'socratic_needed': result.get('socratic_needed', False),
            'socratic_passes': result.get('socratic_passes'),
            'pattern_match': result.get('pattern_match'),
            'bypassed_reasoning': result.get('bypassed_reasoning', False),
            'tom_prediction': result.get('tom_prediction', {}),
            'ollama_available': self.ollama_available
        }
    
    def _map_directive_to_thinking(self, directive: str) -> str:
        """Map NexusOS directive to OpenClaw thinking level"""
        mapping = {
            'STANDARD': 'low',
            'DEEP_ANALYSIS': 'high',
            'ADVERSARIAL_SELF_TEST': 'high',
            'PRIORITIZE_ACTION': 'low',
            'FLAG_UNCERTAINTY': 'medium',
            'MAX_EFFORT': 'high'
        }
        return mapping.get(directive, 'low')
    
    def get_system_prompt_additions(self, nexusos_result: dict) -> str:
        """
        Get additions to system prompt based on NexusOS processing.
        These get prepended to the actual prompt.
        """
        additions = []
        
        directive = nexusos_result.get('directive', 'STANDARD')
        
        if directive == 'ADVERSARIAL_SELF_TEST':
            additions.append("CRITICAL: Run adversarial self-check before responding. What could go wrong?")
        
        elif directive == 'PRIORITIZE_ACTION':
            additions.append("URGENT: Respond concisely and immediately. No fluff.")
        
        elif directive == 'FLAG_UNCERTAINTY':
            additions.append("NOTE: Explicitly acknowledge uncertainty in your response.")
        
        elif directive == 'MAX_EFFORT':
            additions.append("IMPORTANT: This connects to core goals. Go all-in on thoroughness.")
        
        # Add TOM prediction if strong
        tom = nexusos_result.get('tom_prediction', {})
        if tom.get('confidence', 0) > 0.7:
            additions.append(f"User likely wants: {tom.get('answer', '')[:100]}")
        
        return " ".join(additions)


# Singleton instance
nexusos = NexusOSIntegration()


def quick_affect(message: str) -> str:
    """Quick affect analysis only - lightweight"""
    signals = affect_layer.analyze(message)
    return affect_layer.get_processing_directive(signals)


def should_run_socratic(message: str) -> bool:
    """Quick check if message needs socratic dialogue"""
    return socratic.is_significant(message)


# Test if loaded
if __name__ == '__main__':
    print(f"NexusOS Integration loaded")
    print(f"Ollama available: {nexusos.ollama_available}")
    
    # Quick test
    test_msg = "Build NexusOS with continuous background processing"
    result = nexusos.process(test_msg)
    print(f"\nTest message: {test_msg}")
    print(f"Directive: {result['directive']}")
    print(f"Thinking: {result['thinking_level']}")