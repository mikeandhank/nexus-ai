"""
Inner Life Package - Six-Layer Architecture
==========================================
The complete Inner Life system for NexusOS agents.

This is the core moat: agents with genuine personality, persistent memory,
and cumulative learning that compounds over time.

Usage:
    from inner_life import get_inner_life
    
    # Get the Inner Life engine for a user
    inner_life = get_inner_life("user123")
    
    # Process a message through all layers
    context = inner_life.process("Hello, how are you?")
    
    # Remember something important
    inner_life.remember("Michael prefers brief bullet points", "preference", 0.9)
    
    # Recall relevant memories
    memory = inner_life.recall("preferences")
    
    # Get status
    status = inner_life.get_status()
"""

from .engine import InnerLifeEngine, get_inner_life
from .memory_graph import CumulativeMemoryGraph, get_memory_graph

__all__ = [
    "InnerLifeEngine",
    "get_inner_life",
    "CumulativeMemoryGraph", 
    "get_memory_graph"
]