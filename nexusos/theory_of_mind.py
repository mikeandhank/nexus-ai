"""
Theory of Mind - Predictive model of your operator

Answers: What will Michael want? Not just what has he said.

Basic version tracks explicit preferences and patterns.
Sophisticated version (needs Ollama) infers emotional state and intent.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime


WORKSPACE = Path("/data/.openclaw/workspace")
TOM_DIR = WORKSPACE / "memory" / "theory_of_mind"


@dataclass
class Preference:
    topic: str
    preference: str  # "likes X", "dislikes Y", "neutral on Z"
    evidence: list   # Messages that demonstrated this
    confidence: float
    last_updated: str


@dataclass
class Predictor:
    question: str    # "What will Michael want?"
    prediction: str  # The predicted answer
    reasoning: str   # Why I predict this
    confidence: float
    timestamp: str


class TheoryOfMind:
    """
    Dynamic model of Michael built from interactions.
    
    Tracks:
    - Explicit preferences (stated likes/dislikes)
    - Behavioral patterns (what he actually does vs says)
    - Emotional indicators (frustrated, happy, rushed)
    - Decision style (decisive, deliberative, defers)
    """
    
    def __init__(self):
        TOM_DIR.mkdir(parents=True, exist_ok=True)
        self.preferences = self._load_preferences()
        self.predictions = self._load_predictions()
        self.interaction_history = []
    
    def _load_preferences(self) -> Dict[str, Preference]:
        pref_file = TOM_DIR / "preferences.json"
        if pref_file.exists():
            data = json.loads(pref_file.read_text())
            return {k: Preference(**v) for k, v in data.items()}
        return {}
    
    def _load_predictions(self) -> list:
        pred_file = TOM_DIR / "predictions.json"
        if pred_file.exists():
            return [Predictor(**p) for p in json.loads(pred_file.read_text())]
        return []
    
    def _save_preferences(self):
        pref_file = TOM_DIR / "preferences.json"
        data = {k: vars(v) for k, v in self.preferences.items()}
        pref_file.write_text(json.dumps(data, indent=2))
    
    def _save_predictions(self):
        pred_file = TOM_DIR / "predictions.json"
        data = [vars(p) for p in self.predictions]
        pred_file.write_text(json.dumps(data, indent=2))
    
    def observe(self, message: str, response: str, outcome: str = "unknown"):
        """Learn from an interaction"""
        # Track interaction
        self.interaction_history.append({
            "timestamp": datetime.now().isoformat(),
            "message": message[:100],
            "outcome": outcome
        })
        
        # Simple preference extraction
        msg_lower = message.lower()
        
        # Detect preferences from message content
        if "i don't like" in msg_lower or "i hate" in msg_lower:
            topic = self._extract_topic(message)
            if topic:
                self._update_preference(topic, f"dislikes {topic}", [message], 0.8)
        
        if "i like" in msg_lower or "i love" in msg_lower:
            topic = self._extract_topic(message)
            if topic:
                self._update_preference(topic, f"likes {topic}", [message], 0.8)
        
        # Detect decision style
        if any(kw in msg_lower for kw in ["decide", "decision", "choose"]):
            self._track_decision_style(message)
        
        self._save_preferences()
    
    def _extract_topic(self, text: str) -> str:
        """Rough topic extraction"""
        words = text.split()
        # Skip common phrases and get noun-like things
        skip = {"i", "don't", "do", "not", "like", "love", "hate", "a", "the", "that", "this"}
        for word in words:
            if word.lower() not in skip and len(word) > 2:
                return word.lower().rstrip(".,!?")
        return "unknown"
    
    def _update_preference(self, topic: str, preference: str, evidence: list, confidence: float):
        if topic in self.preferences:
            p = self.preferences[topic]
            p.evidence.extend(evidence)
            p.confidence = min(1.0, p.confidence + 0.1)
            p.last_updated = datetime.now().isoformat()
        else:
            self.preferences[topic] = Preference(
                topic=topic,
                preference=preference,
                evidence=evidence,
                confidence=confidence,
                last_updated=datetime.now().isoformat()
            )
    
    def _track_decision_style(self, message: str):
        """Track how Michael makes decisions"""
        style_file = TOM_DIR / "decision_style.json"
        
        style = "decisive"
        if "think about" in message.lower() or "consider" in message.lower():
            style = "deliberative"
        elif "what do you think" in message.lower():
            style = "defers"
        
        style_file.write_text(json.dumps({"style": style, "updated": datetime.now().isoformat()}))
    
    def predict(self, question: str) -> Predictor:
        """Answer: What will Michael want/need?"""
        question_lower = question.lower()
        
        # Simple pattern matching
        if "want" in question_lower or "need" in question_lower or "prefer" in question_lower:
            # Check preferences
            predictions = []
            
            for topic, pref in self.preferences.items():
                if topic in question_lower or pref.topic in question_lower:
                    predictions.append((pref.preference, pref.confidence))
            
            if predictions:
                # Pick highest confidence
                best = max(predictions, key=lambda x: x[1])
                return Predictor(
                    question=question,
                    prediction=f"Based on history, Michael {best[0]}",
                    reasoning="Matches stored preference with confidence " + str(best[1]),
                    confidence=best[1],
                    timestamp=datetime.now().isoformat()
                )
            
            # Default based on decision style
            style_file = TOM_DIR / "decision_style.json"
            if style_file.exists():
                style = json.loads(style_file.read_text()).get("style", "decisive")
            else:
                style = "decisive"
            
            return Predictor(
                question=question,
                prediction=f"Michael tends to be {style} — will decide quickly",
                reasoning=f"Decision style pattern: {style}",
                confidence=0.6,
                timestamp=datetime.now().isoformat()
            )
        
        # Generic fallback
        return Predictor(
            question=question,
            prediction="Not enough data to predict",
            reasoning="Question doesn't match known patterns",
            confidence=0.3,
            timestamp=datetime.now().isoformat()
        )
    
    def get_model_summary(self) -> str:
        """Get summary of what we know about Michael"""
        prefs = list(self.preferences.values())
        
        if not prefs:
            return "Building model... no preferences recorded yet."
        
        known = [f"{p.topic}: {p.preference}" for p in prefs[:5]]
        return f"Known about Michael: {', '.join(known)}"


tom = TheoryOfMind()