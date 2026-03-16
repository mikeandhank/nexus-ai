"""
MCP Agent Memory Tools
Tools for agents to store and retrieve persistent memory
"""
import json
import time
from typing import Dict, List, Any
import redis
import os


class AgentMemory:
    """
    Persistent memory store for agents using Redis
    """
    
    def __init__(self, redis_url: str = None):
        self.redis = redis.from_url(redis_url or os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.key_prefix = "agent:memory:"
    
    def _get_key(self, agent_id: str, memory_type: str = "episodic") -> str:
        return f"{self.key_prefix}{agent_id}:{memory_type}"
    
    def store(
        self, 
        agent_id: str, 
        content: str, 
        memory_type: str = "episodic",
        metadata: Dict = None
    ) -> Dict:
        """
        Store a memory entry
        
        Args:
            agent_id: The agent's ID
            content: The memory content
            memory_type: episodic, semantic, or working
            metadata: Optional metadata (source, importance, etc.)
        """
        entry = {
            "id": f"{agent_id}:{int(time.time() * 1000)}",
            "content": content,
            "type": memory_type,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        key = self._get_key(agent_id, memory_type)
        self.redis.zadd(key, {json.dumps(entry): time.time()})
        
        # Set TTL for automatic cleanup (30 days)
        self.redis.expire(key, 30 * 86400)
        
        return {"success": True, "memory_id": entry["id"]}
    
    def retrieve(
        self, 
        agent_id: str, 
        memory_type: str = "episodic",
        limit: int = 10,
        since: float = None
    ) -> List[Dict]:
        """
        Retrieve memories
        
        Args:
            agent_id: The agent's ID
            memory_type: episodic, semantic, or working
            limit: Maximum memories to return
            since: Optional timestamp to retrieve memories after
        """
        key = self._get_key(agent_id, memory_type)
        
        if since:
            memories = self.redis.zrangebyscore(key, since, "+inf")
        else:
            memories = self.redis.zrevrange(key, 0, limit - 1)
        
        return [json.loads(m) for m in memories]
    
    def search(
        self, 
        agent_id: str, 
        query: str,
        memory_type: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search memories for content
        """
        results = []
        types = [memory_type] if memory_type else ["episodic", "semantic", "working"]
        
        for mtype in types:
            key = self._get_key(agent_id, mtype)
            memories = self.redis.zrange(key, 0, -1)
            
            for m in memories:
                entry = json.loads(m)
                if query.lower() in entry["content"].lower():
                    entry["type"] = mtype
                    results.append(entry)
                    if len(results) >= limit:
                        return results
        
        return results[:limit]
    
    def delete(
        self, 
        agent_id: str, 
        memory_id: str = None,
        memory_type: str = None
    ) -> Dict:
        """
        Delete memories
        """
        if memory_id:
            # Delete specific memory
            for mtype in ["episodic", "semantic", "working"]:
                key = self._get_key(agent_id, mtype)
                memories = self.redis.zrange(key, 0, -1)
                for m in memories:
                    entry = json.loads(m)
                    if entry["id"] == memory_id:
                        self.redis.zrem(key, m)
                        return {"success": True}
            return {"success": False, "error": "Memory not found"}
        elif memory_type:
            # Delete all of type
            key = self._get_key(agent_id, memory_type)
            self.redis.delete(key)
            return {"success": True}
        else:
            # Delete all
            for mtype in ["episodic", "semantic", "working"]:
                self.redis.delete(self._get_key(agent_id, mtype))
            return {"success": True}
    
    def count(self, agent_id: str, memory_type: str = None) -> int:
        """Get count of memories"""
        if memory_type:
            return self.redis.zcard(self._get_key(agent_id, memory_type))
        
        total = 0
        for mtype in ["episodic", "semantic", "working"]:
            total += self.redis.zcard(self._get_key(agent_id, mtype))
        return total


# Global instance
_memory = None

def get_memory() -> AgentMemory:
    global _memory
    if _memory is None:
        _memory = AgentMemory()
    return _memory


# MCP Tool Functions

def memory_store(agent_id: str, content: str, memory_type: str = "episodic", **kwargs) -> Dict:
    """Store a memory"""
    return get_memory().store(agent_id, content, memory_type, kwargs)

def memory_retrieve(agent_id: str, memory_type: str = "episodic", limit: int = 10, **kwargs) -> Dict:
    """Retrieve memories"""
    return {"memories": get_memory().retrieve(agent_id, memory_type, limit)}

def memory_search(agent_id: str, query: str, limit: int = 5, **kwargs) -> Dict:
    """Search memories"""
    return {"results": get_memory().search(agent_id, query, limit=limit)}

def memory_delete(agent_id: str, memory_id: str = None, memory_type: str = None, **kwargs) -> Dict:
    """Delete memories"""
    return get_memory().delete(agent_id, memory_id, memory_type)

def memory_count(agent_id: str, memory_type: str = None, **kwargs) -> Dict:
    """Count memories"""
    return {"count": get_memory().count(agent_id, memory_type)}
