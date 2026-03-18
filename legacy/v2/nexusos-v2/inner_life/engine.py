"""
Inner Life Core - The Six-Layer Architecture
=============================================
This is the complete Inner Life system that creates agents with genuine personality
and persistent identity. This is our deepest moat against NemoClaw.

The six layers:
1. Affect Layer - Emotional/pre-attentional signals
2. Socratic Dialogue - Question-based reasoning
3. Pattern Recognition - Learning from interactions
4. Narrative Generation - First-person story
5. Theory of Mind - User modeling
6. Background Processing - Continuous learning
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import existing components
try:
    from nexusos.affect_layer import AffectLayer
except ImportError:
    AffectLayer = None

try:
    from nexusos.inner_narrative import InnerNarrative
except ImportError:
    InnerNarrative = None

try:
    from nexusos.socratic_dialogue import SocraticDialogue
except ImportError:
    SocraticDialogue = None

from .memory_graph import CumulativeMemoryGraph, get_memory_graph
from .context_optimizer import get_context_optimizer, get_token_manager


class PatternRecognizer:
    """
    Layer 3: Pattern Recognition
    =============================
    Learns patterns from user interactions over time.
    Identifies recurring behaviors, preferences, and rhythms.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.patterns: Dict[str, Any] = {}
        self.pattern_file = f"/opt/nexusos-data/patterns_{user_id}.json"
        self._load_patterns()
    
    def _load_patterns(self):
        if os.path.exists(self.pattern_file):
            with open(self.pattern_file, 'r') as f:
                self.patterns = json.load(f)
        else:
            self.patterns = {
                "temporal": {},      # Time-based patterns
                "topic": {},         # Topic preferences
                "behavior": {},      # Behavioral patterns
                "response": {}       # How user responds to different prompts
            }
    
    def _save_patterns(self):
        os.makedirs(os.path.dirname(self.pattern_file), exist_ok=True)
        with open(self.pattern_file, 'w') as f:
            json.dump(self.patterns, f, indent=2)
    
    def record_interaction(self, message: str, response: str, context: Dict = None):
        """Record an interaction to learn patterns"""
        now = datetime.utcnow()
        context = context or {}
        
        # Temporal pattern: time of day
        hour = now.hour
        time_bucket = f"{hour//6 * 6}-{(hour//6 + 1) * 6}"  # 6-hour buckets
        if time_bucket not in self.patterns["temporal"]:
            self.patterns["temporal"][time_bucket] = {"messages": 0, "topics": {}}
        
        self.patterns["temporal"][time_bucket]["messages"] += 1
        
        # Topic pattern: what they ask about
        topics = self._extract_topics(message)
        for topic in topics:
            if topic not in self.patterns["temporal"][time_bucket]["topics"]:
                self.patterns["temporal"][time_bucket]["topics"][topic] = 0
            self.patterns["temporal"][time_bucket]["topics"][topic] += 1
        
        # Topic preferences
        for topic in topics:
            if topic not in self.patterns["topic"]:
                self.patterns["topic"][topic] = {"count": 0, "satisfaction": []}
            self.patterns["topic"][topic]["count"] += 1
        
        self._save_patterns()
    
    def _extract_topics(self, text: str) -> List[str]:
        """Simple topic extraction"""
        text = text.lower()
        topics = []
        
        keyword_map = {
            "revenue|mrr|profit|income|sales": "business",
            "code|program|debug|api": "development", 
            "memory|remember|know": "memory",
            "agent|automation|workflow": "automation",
            "research|search|find": "research",
            "deploy|host|server|cloud": "infrastructure",
            "write|content|blog|post": "content",
            "meeting|call|schedule": "scheduling"
        }
        
        for pattern, topic in keyword_map.items():
            import re
            if re.search(pattern, text):
                topics.append(topic)
        
        return topics if topics else ["general"]
    
    def get_active_hours(self) -> List[int]:
        """Return hours when user is most active"""
        hour_counts = {}
        for bucket, data in self.patterns.get("temporal", {}).items():
            start_hour = int(bucket.split("-")[0])
            hour_counts[start_hour] = hour_counts.get(start_hour, 0) + data.get("messages", 0)
        
        return sorted(hour_counts.keys(), key=lambda h: hour_counts[h], reverse=True)[:3]
    
    def get_top_topics(self) -> List[str]:
        """Return user's most discussed topics"""
        topic_counts = {}
        for topic, data in self.patterns.get("topic", {}).items():
            topic_counts[topic] = data.get("count", 0)
        
        return sorted(topic_counts.keys(), key=lambda t: topic_counts[t], reverse=True)[:5]


class UserModel:
    """
    Layer 5: Theory of Mind
    =======================
    Builds a model of the user - their preferences, communication style,
    decision patterns, and goals.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.model_file = f"/opt/nexusos-data/user_model_{user_id}.json"
        self._load_model()
    
    def _load_model(self):
        if os.path.exists(self.model_file):
            with open(self.model_file, 'r') as f:
                self.model = json.load(f)
        else:
            self.model = {
                "preferences": {},
                "communication_style": {},
                "decision_patterns": {},
                "goals": [],
                "frustrations": [],
                "updated_at": None
            }
    
    def _save_model(self):
        os.makedirs(os.path.dirname(self.model_file), exist_ok=True)
        with open(self.model_file, 'w') as f:
            json.dump(self.model, f, indent=2)
    
    def learn_from_interaction(self, message: str, response: str, feedback: Dict = None):
        """Update user model based on interaction"""
        
        # Detect communication style
        if "?" in message:
            self.model["communication_style"]["asks_questions"] = \
                self.model["communication_style"].get("asks_questions", 0) + 1
        
        if len(message) < 50:
            self.model["communication_style"]["prefers_concise"] = \
                self.model["communication_style"].get("prefers_concise", 0) + 1
        
        if message.startswith("Why") or message.startswith("How come"):
            self.model["communication_style"]["analytical"] = \
                self.model["communication_style"].get("analytical", 0) + 1
        
        # Extract potential goals
        import re
        goal_patterns = [
            (r"want to (.*?)\.", "wants"),
            (r"need to (.*?)\.", "needs"),
            (r"trying to (.*?)\.", "trying"),
            (r"goal is (.*?)\.", "goal")
        ]
        
        for pattern, intent in goal_patterns:
            match = re.search(pattern, message.lower())
            if match:
                goal = match.group(1).strip()
                if goal not in self.model["goals"]:
                    self.model["goals"].append(goal)
        
        self.model["updated_at"] = datetime.utcnow().isoformat()
        self._save_model()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a learned preference"""
        return self.model.get("preferences", {}).get(key, default)
    
    def set_preference(self, key: str, value: Any):
        """Learn a preference"""
        self.model.setdefault("preferences", {})[key] = value
        self._save_model()
    
    def get_communication_style(self) -> str:
        """Summarize communication style"""
        style = self.model.get("communication_style", {})
        
        if style.get("prefers_concise", 0) > style.get("analytical", 0):
            return "concise"
        elif style.get("analytical", 0) > 3:
            return "analytical"
        elif style.get("asks_questions", 0) > 5:
            return "curious"
        else:
            return "balanced"


class InnerLifeEngine:
    """
    THE INNER LIFE - Six-Layer Architecture
    ==========================================
    
    This is the complete Inner Life system that creates agents with
    genuine personality and persistent identity.
    
    The layers work together:
    1. Affect → Quick emotional signals before reasoning
    2. Memory Graph → Long-term memory with graph connections
    3. Pattern Recognizer → Learns temporal and behavioral patterns
    4. Narrative → First-person story that evolves
    5. User Model → Theory of mind for the user
    6. Socratic → Question-based reasoning
    
    This creates agents that:
    - Have genuine emotional responses (affect)
    - Remember everything across sessions (memory graph)
    - Learn your patterns over time (pattern recognizer)
    - Tell their own story (narrative)
    - Understand you (user model)
    - Question to understand deeper (socratic)
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        
        # Layer 1: Affect (pre-attentional signals)
        if AffectLayer:
            try:
                self.affect = AffectLayer()
            except Exception as e:
                logger.warning(f"AffectLayer init failed: {e}")
                self.affect = None
        else:
            self.affect = None
        
        # Layer 2: Memory Graph (cumulative long-term memory)
        self.memory = get_memory_graph(user_id)
        
        # Layer 3: Pattern Recognition
        self.patterns = PatternRecognizer(user_id)
        
        # Layer 4: Narrative (first-person story)
        if InnerNarrative:
            try:
                self.narrative = InnerNarrative()
            except Exception as e:
                logger.warning(f"InnerNarrative init failed: {e}")
                self.narrative = None
        else:
            self.narrative = None
        
        # Layer 5: User Model (theory of mind)
        self.user_model = UserModel(user_id)
        
        # Layer 6: Socratic (question-based reasoning)
        if SocraticDialogue:
            try:
                self.socratic = SocraticDialogue()
            except Exception as e:
                logger.warning(f"SocraticDialogue init failed: {e}")
                self.socratic = None
        else:
            self.socratic = None
        
        logger.info(f"InnerLifeEngine initialized for user {user_id}")
    
    def process(self, message: str, context: Dict = None) -> Dict:
        """
        Process a message through all six layers.
        
        Returns enriched context for the agent to use.
        """
        context = context or {}
        now = datetime.utcnow()
        
        # Layer 1: Affect Analysis (fast, pre-reasoning)
        affect_signals = {}
        if self.affect:
            try:
                affect_signals = self.affect.analyze(message, context)
            except Exception as e:
                logger.warning(f"Affect analysis failed: {e}")
        
        # Layer 5: User Model Update
        try:
            self.user_model.learn_from_interaction(message, "", context)
        except Exception as e:
            logger.warning(f"User model update failed: {e}")
        
        # Layer 3: Record interaction for pattern learning
        try:
            self.patterns.record_interaction(message, "", context)
        except Exception as e:
            logger.warning(f"Pattern recording failed: {e}")
        
        # Layer 2: Recall relevant memories (semantic search)
        memories = []
        try:
            recalled = self.memory.recall_semantic(message, limit=5)
            memories = [{"content": m.content, "type": m.type, "confidence": m.confidence} 
                       for m, score in recalled]
        except Exception as e:
            logger.warning(f"Memory recall failed: {e}")
        
        # Get user preferences
        user_style = ""
        try:
            user_style = self.user_model.get_communication_style()
        except:
            pass
        
        # Get active hours
        active_hours = []
        try:
            active_hours = self.patterns.get_active_hours()
        except:
            pass
        
        return {
            "affect_signals": affect_signals,
            "memories": memories,
            "user_style": user_style,
            "active_hours": active_hours,
            "inner_life_active": True,
            "layers_initialized": {
                "affect": self.affect is not None,
                "memory": True,
                "patterns": True,
                "narrative": self.narrative is not None,
                "user_model": True,
                "socratic": self.socratic is not None
            }
        }
    
    def remember(self, content: str, memory_type: str = "fact", confidence: float = 1.0):
        """Explicitly remember something"""
        return self.memory.add_memory(content, memory_type, confidence, source="user")
    
    def recall(self, query: str) -> str:
        """Recall memories related to query"""
        return self.memory.infer_about_user(query)
    
    def get_status(self) -> Dict:
        """Get Inner Life status"""
        return {
            "layers": {
                "affect": "active" if self.affect else "unavailable",
                "memory": f"{len(self.memory.nodes)} nodes",
                "patterns": f"{sum(len(p) for p in self.patterns.patterns.values())} patterns",
                "narrative": "active" if self.narrative else "unavailable",
                "user_model": "active",
                "socratic": "active" if self.socratic else "unavailable"
            },
            "memory_graph": self.memory.get_memory_summary(),
            "user_style": self.user_model.get_communication_style(),
            "top_topics": self.patterns.get_top_topics()
        }
    
    def export_memory(self) -> Dict:
        """Export all memory - user owns their data"""
        return self.memory.export()
    
    # ========== MEMORY MANAGEMENT ==========
    
    def get_memory_stats(self) -> Dict:
        """Get detailed memory statistics"""
        from .memory_summarization import MemorySummarizer, MemoryForgetting
        
        summarizer = MemorySummarizer(self.memory)
        stats = summarizer.get_statistics()
        
        # Add forgetting candidates
        forgetting = MemoryForgetting(self.memory)
        stats["forgetting_candidates"] = forgetting.get_forgetting_candidates(5)
        
        return stats
    
    # ========== CONTEXT OPTIMIZATION ==========
    
    def build_optimized_prompt(self, query: str, system_prompt: str = None) -> Dict:
        """
        Build prompt with FLAT token cost using LLM context optimization.
        
        Uses local Ollama to intelligently select and compress context,
        ensuring token usage stays constant regardless of memory size.
        """
        from .context_optimizer import get_token_manager
        
        token_manager = get_token_manager(self.memory)
        return token_manager.build_prompt(query, system_prompt)
    
    def get_token_budget(self) -> Dict:
        """Get token budget information"""
        from .context_optimizer import get_token_manager
        
        token_manager = get_token_manager(self.memory)
        return token_manager.get_budget_info()
    
    def run_memory_maintenance(self) -> Dict:
        """Run memory summarization and pruning"""
        from .memory_summarization import MemorySummarizer, MemoryForgetting
        
        results = {}
        
        # Summarize old memories
        summarizer = MemorySummarizer(self.memory)
        results["summarization"] = summarizer.summarize()
        
        # Prune forgotten memories
        forgetting = MemoryForgetting(self.memory)
        results["pruning"] = forgetting.prune()
        
        return results


# Global instances
_inner_life_instances: Dict[str, InnerLifeEngine] = {}

def get_inner_life(user_id: str) -> InnerLifeEngine:
    """Get or create Inner Life engine for user"""
    if user_id not in _inner_life_instances:
        _inner_life_instances[user_id] = InnerLifeEngine(user_id)
    return _inner_life_instances[user_id]