"""
NexusOS v2 - Skill System

Skill registry and execution for NexusOS.
Allows users to create, share, and execute skills.
"""

import os
import json
import uuid
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Skill:
    """Represents a skill in NexusOS."""
    
    def __init__(self, skill_id: str, name: str, description: str = "", 
                 triggers: List[str] = None, actions: List[str] = None,
                 code: str = None, user_id: str = None, is_public: bool = False):
        self.id = skill_id
        self.name = name
        self.description = description
        self.triggers = triggers or []
        self.actions = actions or []
        self.code = code
        self.user_id = user_id
        self.is_public = is_public
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "triggers": self.triggers,
            "actions": self.actions,
            "user_id": self.user_id,
            "is_public": self.is_public,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SkillRegistry:
    """
    Registry for managing skills.
    
    Skills can be:
    - Triggered by events (file changes, messages, etc.)
    - Executed as actions
    - Shared publicly or kept private
    """
    
    def __init__(self, db=None):
        self.db = db
        self.runtime_skills: Dict[str, Callable] = {}
        
        # Built-in skills
        self._register_builtin_skills()
    
    def _register_builtin_skills(self):
        """Register built-in skills."""
        
        # Welcome skill
        self.register_runtime("welcome", self._skill_welcome)
        
        # Help skill
        self.register_runtime("help", self._skill_help)
        
        # Remember skill (stores to semantic memory)
        self.register_runtime("remember", self._skill_remember)
        
        # Recall skill (retrieves from memory)
        self.register_runtime("recall", self._skill_recall)
        
        # Analyze skill (analyzes content)
        self.register_runtime("analyze", self._skill_analyze)
        
        logger.info("Registered builtin skills")
    
    def register_runtime(self, name: str, func: Callable):
        """Register a runtime skill (code-based)."""
        self.runtime_skills[name] = func
        logger.info(f"Registered runtime skill: {name}")
    
    def create_skill(self, name: str, description: str = "", 
                    triggers: List[str] = None, actions: List[str] = None,
                    code: str = None, user_id: str = None, is_public: bool = False) -> Skill:
        """Create a new skill."""
        skill_id = uuid.uuid4().hex
        
        skill = Skill(
            skill_id=skill_id,
            name=name,
            description=description,
            triggers=triggers,
            actions=actions,
            code=code,
            user_id=user_id,
            is_public=is_public
        )
        
        # Save to database if available
        if self.db:
            self.db.create_skill(skill)
        
        logger.info(f"Created skill: {name} ({skill_id})")
        return skill
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get skill by ID."""
        if self.db:
            skill_data = self.db.get_skill(skill_id)
            if skill_data:
                return Skill(**skill_data)
        return None
    
    def get_skills(self, user_id: str = None, include_public: bool = True) -> List[Skill]:
        """Get user's skills and public skills."""
        skills = []
        
        if self.db:
            skills_data = self.db.get_skills(user_id, include_public)
            for s in skills_data:
                skills.append(Skill(**s))
        
        return skills
    
    def execute_skill(self, skill_name: str, context: Dict = None) -> Any:
        """Execute a runtime skill."""
        if skill_name not in self.runtime_skills:
            raise ValueError(f"Skill '{skill_name}' not found")
        
        func = self.runtime_skills[skill_name]
        return func(context or {})
    
    def match_trigger(self, trigger: str, message: str = None, event: Dict = None) -> List[Skill]:
        """Find skills that match a trigger."""
        matched = []
        
        for skill in self.get_skills(include_public=True):
            # Check trigger matches
            if skill.triggers:
                for t in skill.triggers:
                    if message and t.lower() in message.lower():
                        matched.append(skill)
                    elif event and event.get('type') == t:
                        matched.append(skill)
        
        return matched
    
    # Built-in skill implementations
    def _skill_welcome(self, context: Dict) -> str:
        """Welcome skill - returns welcome message."""
        user_name = context.get('user_name', 'User')
        return f"Welcome to NexusOS, {user_name}! I'm your AI assistant with inner life. How can I help you today?"
    
    def _skill_help(self, context: Dict) -> str:
        """Help skill - returns available commands."""
        return """Available commands:
- remember [fact]: Store a fact in memory
- recall [query]: Search your memory
- analyze [text]: Analyze text for insights
- tools: List available tools
- skills: List available skills

You can also just chat naturally with me!"""
    
    def _skill_remember(self, context: Dict) -> str:
        """Remember skill - stores to semantic memory."""
        fact = context.get('fact')
        user_id = context.get('user_id')
        
        if not fact:
            return "What would you like me to remember?"
        
        if self.db and user_id:
            self.db.add_semantic_memory(
                user_id=user_id,
                entity_type='fact',
                entity_name=fact[:50],
                knowledge=fact,
                confidence=0.8
            )
            return f"I've remembered: {fact}"
        
        return "Memory storage not available"
    
    def _skill_recall(self, context: Dict) -> str:
        """Recall skill - retrieves from semantic memory."""
        query = context.get('query')
        user_id = context.get('user_id')
        
        if not query:
            return "What would you like me to recall?"
        
        if self.db and user_id:
            results = self.db.search_semantic_memory(user_id, query)
            if results:
                return "I remember: " + "; ".join([r.get('knowledge', '') for r in results[:3]])
            return f"I don't have any memories about '{query}'"
        
        return "Memory search not available"
    
    def _skill_analyze(self, context: Dict) -> str:
        """Analyze skill - provides basic analysis."""
        text = context.get('text', '')
        
        if not text:
            return "What would you like me to analyze?"
        
        # Basic analysis
        words = text.split()
        return f"""Analysis:
- Word count: {len(words)}
- Character count: {len(text)}
- First word: {words[0] if words else 'none'}
- Last word: {words[-1] if words else 'none'}"""


# Database extension for skills (if not in main database)
class Database:
    """Minimal database interface for skills."""
    
    def create_skill(self, skill: Skill):
        """Create skill - implement with actual DB."""
        pass
    
    def get_skill(self, skill_id: str):
        """Get skill - implement with actual DB."""
        pass
    
    def get_skills(self, user_id: str = None, include_public: bool = True):
        """Get skills - implement with actual DB."""
        return []
    
    def add_semantic_memory(self, user_id: str, entity_type: str, entity_name: str, 
                          knowledge: str, confidence: float = 0.5):
        """Add semantic memory - implement with actual DB."""
        pass
    
    def search_semantic_memory(self, user_id: str, query: str, limit: int = 10):
        """Search semantic memory - implement with actual DB."""
        return []


# Global instance
_skill_registry = None

def get_skill_registry(db=None) -> SkillRegistry:
    """Get skill registry singleton."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry(db)
    return _skill_registry
