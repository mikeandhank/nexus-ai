"""
Memory Summarization - Long-term memory management
================================================
Handles memory accumulation over years by compressing old memories
into summaries while preserving key information.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemorySummarizer:
    """
    Compresses old memories into summaries to prevent context bloat.
    
    Strategy:
    1. Identify old, low-access memories (30+ days, not accessed recently)
    2. Group by topic/theme
    3. Compress into single "summary" memory
    4. Mark original as "archived"
    5. Update confidence based on age
    """
    
    def __init__(self, memory_graph):
        self.memory = memory_graph
        self.summarize_after_days = 30
        self.min_memories_to_summarize = 20
        self.max_memories_per_summary = 50
    
    def should_summarize(self) -> bool:
        """Check if summarization is needed"""
        total = len(self.memory.nodes)
        
        # Check old memories
        old_count = 0
        cutoff = datetime.utcnow() - timedelta(days=self.summarize_after_days)
        
        for node in self.memory.nodes.values():
            if node.created_at < cutoff:
                old_count += 1
        
        # Summarize if enough old memories
        return old_count >= self.min_memories_to_summarize
    
    def get_memories_to_summarize(self) -> List:
        """Get old memories grouped by topic"""
        cutoff = datetime.utcnow() - timedelta(days=self.summarize_after_days)
        old_memories = []
        
        for node in self.memory.nodes.values():
            if node.created_at < cutoff:
                old_memories.append(node)
        
        return old_memories
    
    def group_by_topic(self, memories: List) -> Dict[str, List]:
        """Group memories by inferred topic"""
        topics = {
            "preferences": [],
            "values": [],
            "facts": [],
            "relationships": [],
            "context": [],
            "other": []
        }
        
        for memory in memories:
            content_lower = memory.content.lower()
            
            if any(w in content_lower for w in ["prefer", "like", "dislike", "want", "don't"]):
                topics["preferences"].append(memory)
            elif any(w in content_lower for w in ["goal", "value", "important", "priority"]):
                topics["values"].append(memory)
            elif any(w in content_lower for w in ["know", "learned", "remember"]):
                topics["facts"].append(memory)
            elif any(w in content_lower for w in ["talked", "discussed", "met", "person"]):
                topics["relationships"].append(memory)
            elif any(w in content_lower for w in ["working", "project", "task", "busy"]):
                topics["context"].append(memory)
            else:
                topics["other"].append(memory)
        
        return topics
    
    def create_summary(self, topic: str, memories: List) -> str:
        """Create a summary from grouped memories"""
        if not memories:
            return ""
        
        # Take most recent N memories
        recent = sorted(memories, key=lambda m: m.created_at, reverse=True)[:self.max_memories_per_summary]
        
        # Build summary
        summary_parts = [f"Summary of {topic} (from {len(memories)} memories):"]
        
        for memory in recent:
            date_str = memory.created_at.strftime("%Y-%m")
            summary_parts.append(f"- {date_str}: {memory.content}")
        
        return "\n".join(summary_parts)
    
    def summarize(self) -> Dict:
        """
        Execute summarization process.
        
        Returns summary of what was done.
        """
        if not self.should_summarize():
            return {
                "action": "none",
                "reason": "Not enough old memories to summarize",
                "total_memories": len(self.memory.nodes)
            }
        
        memories = self.get_memories_to_summarize()
        topics = self.group_by_topic(memories)
        
        summaries_created = 0
        archived_count = 0
        
        for topic, topic_memories in topics.items():
            if len(topic_memories) < 3:
                continue  # Need at least 3 to summarize
            
            # Create summary
            summary_text = self.create_summary(topic, topic_memories)
            
            if summary_text:
                # Add summary as new memory
                self.memory.add_memory(
                    content=summary_text,
                    memory_type="summary",
                    confidence=0.7,  # Lower confidence for summaries
                    source="auto_summary"
                )
                
                # Mark originals as archived (we keep them but they're no longer retrieved)
                for memory in topic_memories:
                    memory.type = f"archived_{memory.type}"
                    self.memory._save_node(memory)
                    archived_count += 1
                
                summaries_created += 1
        
        result = {
            "action": "summarized",
            "topics_processed": summaries_created,
            "memories_archived": archived_count,
            "total_memories": len(self.memory.nodes)
        }
        
        logger.info(f"Memory summarization complete: {result}")
        return result
    
    def get_statistics(self) -> Dict:
        """Get memory statistics for decision-making"""
        now = datetime.utcnow()
        stats = {
            "total_memories": len(self.memory.nodes),
            "by_type": {},
            "age_distribution": {
                "last_7_days": 0,
                "7_30_days": 0,
                "30_90_days": 0,
                "90_plus_days": 0
            },
            "needs_summarization": self.should_summarize()
        }
        
        # Count by type
        for node in self.memory.nodes.values():
            stats["by_type"][node.type] = stats["by_type"].get(node.type, 0) + 1
            
            # Age distribution
            age_days = (now - node.created_at).days
            if age_days < 7:
                stats["age_distribution"]["last_7_days"] += 1
            elif age_days < 30:
                stats["age_distribution"]["7_30_days"] += 1
            elif age_days < 90:
                stats["age_distribution"]["30_90_days"] += 1
            else:
                stats["age_distribution"]["90_plus_days"] += 1
        
        return stats


class MemoryForgetting:
    """
    Automatic memory pruning based on:
    - Low confidence (never reinforced)
    - Negative feedback
    - Age without access
    """
    
    def __init__(self, memory_graph):
        self.memory = memory_graph
        self.forget_after_days = 365  # 1 year
        self.min_confidence_to_keep = 0.3
    
    def should_forget(self, memory) -> bool:
        """Determine if memory should be forgotten"""
        now = datetime.utcnow()
        
        # Age check
        age_days = (now - memory.created_at).days
        
        # Access check
        days_since_access = (now - memory.last_accessed).days
        
        # Never accessed and old
        if age_days > self.forget_after_days and days_since_access > 180:
            return True
        
        # Low confidence and not accessed in 90 days
        if memory.confidence < self.min_confidence_to_keep and days_since_access > 90:
            return True
        
        return False
    
    def prune(self) -> Dict:
        """Remove forgotten memories"""
        to_remove = []
        
        for node_id, node in self.memory.nodes.items():
            if self.should_forget(node):
                to_remove.append(node_id)
        
        # Remove from graph
        for node_id in to_remove:
            del self.memory.nodes[node_id]
            
            # Remove edges
            self.memory.edges = [
                e for e in self.memory.edges 
                if e.from_id != node_id and e.to_id != node_id
            ]
        
        result = {
            "forgotten": len(to_remove),
            "remaining": len(self.memory.nodes)
        }
        
        logger.info(f"Memory pruning complete: {result}")
        return result
    
    def get_forgetting_candidates(self, limit: int = 10) -> List[Dict]:
        """Get memories that could be forgotten"""
        candidates = []
        
        for node_id, node in self.memory.nodes.items():
            if self.should_forget(node):
                candidates.append({
                    "id": node_id,
                    "content": node.content[:50] + "...",
                    "age_days": (datetime.utcnow() - node.created_at).days,
                    "confidence": node.confidence,
                    "last_accessed": (datetime.utcnow() - node.last_accessed).days
                })
        
        return candidates[:limit]