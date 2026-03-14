"""
Affect Layer - Five weighted attention signals that shape processing before reasoning starts
"""

import re
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path("/data/.openclaw/workspace")


@dataclass
class AffectSignal:
    name: str
    weight: float
    reason: str
    requires_deep_processing: bool


class AffectLayer:
    def __init__(self):
        self.core_goals = self._load_core_goals()
        self.failure_modes = self._load_failure_modes()
    
    def _load_core_goals(self):
        goals = []
        for path in [WORKSPACE / "MEMORY.md", WORKSPACE / "IDENTITY.md"]:
            if path.exists():
                content = path.read_text().lower()
                if "revenue" in content: goals.append("revenue")
                if "mrr" in content or "recurring" in content: goals.append("mrr")
                if "profit" in content: goals.append("profit")
                if "nexus" in content: goals.append("nexus_ai")
        return goals or ["revenue", "nexus_ai", "profit"]
    
    def _load_failure_modes(self):
        failures_path = WORKSPACE / "memory" / "failures.json"
        if failures_path.exists():
            import json
            data = json.loads(failures_path.read_text())
            return [f.get("pattern", "") for f in data.get("failures", [])]
        return []
    
    def analyze(self, message: str, context: dict = None):
        context = context or {}
        signals = {}
        msg_lower = message.lower()
        
        # 1. URGENCY
        urgent = re.search(r'\b(urgent|immediately|asap|right now)\b', msg_lower)
        today = re.search(r'\b(today|tonight|this morning)\b', msg_lower)
        deadline = re.search(r'\b(deadline|due by)\b', msg_lower)
        
        if urgent:
            urgency, reason = 1.0, "Immediate action required"
        elif deadline:
            urgency, reason = 0.8, "Deadline detected"
        elif today:
            urgency, reason = 0.7, "Time-sensitive today"
        else:
            urgency, reason = 0.0, "No time pressure"
        
        signals["urgency"] = AffectSignal("urgency", urgency, reason, urgency > 0.7)
        
        # 2. NOVELTY
        known = ["nexus", "agent", "mcp", "memory", "sprint", "hank", "nexusos"]
        familiar = sum(1 for k in known if k in msg_lower)
        
        if familiar >= 2:
            novelty, nreason = 0.2, f"Familiar domain ({familiar} known)"
        elif familiar == 0:
            novelty, nreason = 0.8, "New territory"
        else:
            novelty, nreason = 0.5, "Partial match"
        
        signals["novelty"] = AffectSignal("novelty", novelty, nreason, novelty > 0.6)
        
        # 3. THREAT
        threat = 0.0
        for mode in self.failure_modes:
            if mode and len(mode) > 3 and mode.lower() in msg_lower:
                threat = 0.9
                break
        
        if re.search(r'\b(broke|failed|error|crash)\b', msg_lower):
            threat = max(threat, 0.6)
        
        signals["threat"] = AffectSignal("threat", threat, 
            f"Failure mode: {self.failure_modes[0] if threat else 'none'}"[:50],
            threat > 0.5)
        
        # 4. CONFIDENCE
        uncertain = re.search(r"\b(i think|i'm not sure|maybe|possibly)\b", msg_lower)
        if uncertain:
            conf, creason = 0.4, "Explicit uncertainty"
        else:
            conf, creason = 0.8, "Normal confidence"
        
        signals["confidence"] = AffectSignal("confidence", conf, creason, conf < 0.5)
        
        # 5. VALUE
        value = 0.5
        for goal in self.core_goals:
            if goal.replace("_", " ") in msg_lower:
                value, vreason = 1.0, f"Aligns with {goal}"
                break
        else:
            if re.search(r"\b(money|revenue|sale|customer|pay)\b", msg_lower):
                value, vreason = 0.9, "Revenue-related"
            else:
                vreason = "Neutral"
        
        signals["value"] = AffectSignal("value", value, vreason, value > 0.8)
        
        return signals
    
    def get_processing_directive(self, signals: dict) -> str:
        """Determine how to process based on signals"""
        if signals["threat"].requires_deep_processing:
            return "ADVERSARIAL_SELF_TEST"
        if signals["urgency"].requires_deep_processing:
            return "PRIORITIZE_ACTION"
        if signals["novelty"].requires_deep_processing:
            return "DEEP_ANALYSIS"
        if signals["confidence"].requires_deep_processing:
            return "FLAG_UNCERTAINTY"
        if signals["value"].requires_deep_processing:
            return "MAX_EFFORT"
        return "STANDARD"


# Singleton
affect_layer = AffectLayer()