"""
NexusOS Semantic Memory - Vector-based memory with Qdrant support
"""

import os
import uuid
import hashlib
import threading
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False


class MemoryType(Enum):
    CONVERSATION = "conversation"
    FACT = "fact"
    AGENT_CONTEXT = "agent_context"
    USER_PREFERENCE = "user_preference"
    TOOL_RESULT = "tool_result"
    DECISION = "decision"


class EmbeddingGenerator:
    """Generate embeddings for text"""
    
    def __init__(self):
        self._model = None
        self._use_fallback = True
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self._model = SentenceTransformer("all-MiniLM-L6-v2")
                self._use_fallback = False
                print("[Embeddings] Using sentence-transformers")
            except:
                self._use_fallback = True
        if self._use_fallback:
            print("[Embeddings] Using hash fallback")
    
    def encode(self, text: str) -> List[float]:
        if self._model:
            try:
                return self._model.encode(text, normalize_embeddings=True).tolist()
            except:
                pass
        # Fallback: hash-based
        return self._hash_embedding(text)
    
    def _hash_embedding(self, text: str, dim: int = 384) -> List[float]:
        return [(int(hashlib.sha256(f"{text}_{i}".encode()).hexdigest()[:8], 16) / 2**32) * 2 - 1 
                for i in range(dim)]


def cosine_sim(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (sum(x*x for x in a) * sum(y*y for y in b)) ** 0.5 + 1e-10


class SemanticMemory:
    """Vector-based semantic memory"""
    
    def __init__(self, qdrant_url: str = None):
        self.qdrant_url = qdrant_url or os.environ.get('QDRANT_URL', '')
        self._client = None
        self._embed = EmbeddingGenerator()
        self._use_qdrant = False
        self._local: List[Dict] = []
        self._lock = threading.Lock()
        self._init()
    
    def _init(self):
        if not QDRANT_AVAILABLE or not self.qdrant_url:
            print("[SemanticMemory] Using in-memory store")
            return
        try:
            self._client = QdrantClient(url=self.qdrant_url) if self.qdrant_url.startswith('http') else QdrantClient(host=self.qdrant_url.split(':')[0], port=6333)
            self._client.get_collections()
            self._use_qdrant = True
            print(f"[SemanticMemory] Connected to Qdrant")
        except Exception as e:
            print(f"[SemanticMemory] Qdrant unavailable: {e}")
    
    def add(self, content: str, memory_type: MemoryType = MemoryType.CONVERSATION,
            user_id: str = "", agent_id: str = None, metadata: Dict = None) -> str:
        """Add memory with embedding"""
        mid = str(uuid.uuid4())
        emb = self._embed.encode(content)
        
        entry = {
            'id': mid,
            'memory_type': memory_type.value,
            'user_id': user_id,
            'agent_id': agent_id,
            'content': content,
            'metadata': metadata or {},
            'created_at': datetime.utcnow().isoformat(),
            'embedding': emb
        }
        
        if self._use_qdrant and self._client:
            try:
                self._client.upsert(collection_name="nexusos_memory",
                    points=[PointStruct(id=mid, vector=emb, payload=entry)])
                return mid
            except:
                pass
        
        with self._lock:
            self._local.append(entry)
        return mid
    
    def search(self, query: str, user_id: str = None, limit: int = 5) -> List[Dict]:
        """Semantic search"""
        qemb = self._embed.encode(query)
        
        if self._use_qdrant and self._client:
            try:
                results = self._client.search(collection_name="nexusos_memory",
                    query_vector=qemb, limit=limit)
                return [{**r.payload, 'score': r.score} for r in results]
            except:
                pass
        
        # Fallback
        with self._lock:
            scored = [(e, cosine_sim(qemb, e.get('embedding', []))) for e in self._local]
            if user_id:
                scored = [(e, s) for e, s in scored if e.get('user_id') == user_id]
            scored.sort(key=lambda x: x[1], reverse=True)
            return [{**e, 'score': s} for e, s in scored[:limit]]
    
    def get_by_user(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all memories for user"""
        with self._lock:
            user_memories = [e for e in self._local if e.get('user_id') == user_id]
            return sorted(user_memories, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]


# Global instance
_memory: Optional[SemanticMemory] = None

def get_semantic_memory() -> SemanticMemory:
    global _memory
    if _memory is None:
        _memory = SemanticMemory()
    return _memory
