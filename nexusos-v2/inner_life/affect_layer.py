"""
Affect Layer - Pre-attentional emotional signals
=================================================
Five weighted signals that shape processing before reasoning starts.
Works independently without workspace dependencies.
"""

import re
from dataclasses import dataclass
from typing import Dict


@dataclass
class AffectSignal:
    name: str
    weight: float
    reason: str
    requires_deep_processing: bool


class StandaloneAffectLayer:
    """
    Pre-attentional affect system.
    
    Processes messages through 5 signals:
    1. Urgency - Time sensitivity
    2. Novelty - Familiarity with domain
    3. Threat - Risk/failure detection
    4. Opportunity - Upside detection
    5. Connection - Relationship context
    """
    
    def __init__(self, user_preferences: Dict = None):
        self.user_preferences = user_preferences or {}
        
        # Known domains from this user (will be learned)
        self.known_domains = self.user_preferences.get("known_domains", [
            "nexusos", "ai", "agents", "api", "deployment", "memory"
        ])
        
        # Known people
        self.known_people = self.user_preferences.get("known_people", [
            "michael", "hank"
        ])
    
    def analyze(self, message: str, context: Dict = None) -> Dict:
        """
        Analyze message and return affect signals.
        
        Returns dict of signal_name -> AffectSignal
        """
        context = context or {}
        msg_lower = message.lower()
        
        signals = {}
        
        # 1. URGENCY - Time sensitivity
        signals["urgency"] = self._analyze_urgency(msg_lower)
        
        # 2. NOVELTY - Familiarity
        signals["novelty"] = self._analyze_novelty(msg_lower)
        
        # 3. THREAT - Risk detection
        signals["threat"] = self._analyze_threat(msg_lower, context)
        
        # 4. OPPORTUNITY - Upside detection
        signals["opportunity"] = self._analyze_opportunity(msg_lower)
        
        # 5. CONNECTION - Relationship context
        signals["connection"] = self._analyze_connection(msg_lower, context)
        
        return signals
    
    def _analyze_urgency(self, msg: str) -> AffectSignal:
        """Detect time sensitivity"""
        urgent = re.search(r'\b(urgent|immediately|asap|right now|critical)\b', msg)
        deadline = re.search(r'\b(deadline|due by|by end of)\b', msg)
        today = re.search(r'\b(today|tonight|this morning|by tonight)\b', msg)
        
        if urgent:
            return AffectSignal("urgency", 1.0, "Immediate action required", True)
        elif deadline:
            return AffectSignal("urgency", 0.8, "Deadline detected", True)
        elif today:
            return AffectSignal("urgency", 0.7, "Time-sensitive today", False)
        else:
            return AffectSignal("urgency", 0.0, "No time pressure", False)
    
    def _analyze_novelty(self, msg: str) -> AffectSignal:
        """Detect novelty/familiarity"""
        known_count = sum(1 for domain in self.known_domains if domain in msg)
        
        if known_count >= 3:
            return AffectSignal("novelty", 0.1, f"Familiar domain ({known_count} known terms)", False)
        elif known_count == 0:
            return AffectSignal("novelty", 0.9, "New territory", True)
        else:
            return AffectSignal("novelty", 0.5, "Partial match", False)
    
    def _analyze_threat(self, msg: str, context: Dict) -> AffectSignal:
        """Detect risk/threat"""
        threat_words = r'\b(broken|failed|error|crash|down|lost|deleted|hack|breach|security|problem|issue|wrong)\b'
        if re.search(threat_words, msg):
            # Check severity
            critical = re.search(r'\b(critical|disaster|catastrophic)\b', msg)
            if critical:
                return AffectSignal("threat", 1.0, "Critical threat detected", True)
            return AffectSignal("threat", 0.6, "Potential issue", True)
        
        return AffectSignal("threat", 0.0, "No threat detected", False)
    
    def _analyze_opportunity(self, msg: str) -> AffectSignal:
        """Detect opportunity"""
        opportunity_words = r'\b(opportunity|potential|growth|revenue|profit|improve|better|faster|new|could|should|why not)\b'
        if re.search(opportunity_words, msg):
            return AffectSignal("opportunity", 0.7, "Positive opportunity detected", False)
        
        return AffectSignal("opportunity", 0.0, "No opportunity signal", False)
    
    def _analyze_connection(self, msg: str, context: Dict) -> AffectSignal:
        """Detect relationship context"""
        # Check for personal references
        personal = re.search(r'\b(thanks|please|appreciate|good job|great|work|well)\b', msg)
        if personal:
            return AffectSignal("connection", 0.6, "Positive relationship context", False)
        
        # Check for direct command
        if msg.startswith(("do", "make", "build", "fix", "create", "run")):
            return AffectSignal("connection", 0.3, "Task-oriented", False)
        
        return AffectSignal("connection", 0.0, "Neutral", False)
    
    def get_processing_guidance(self, signals: Dict) -> Dict:
        """Get guidance for how to process based on signals"""
        # Calculate total urgency
        total_urgency = signals.get("urgency", AffectSignal("urgency", 0, "", False)).weight
        total_threat = signals.get("threat", AffectSignal("threat", 0, "", False)).weight
        
        if total_urgency > 0.7 or total_threat > 0.7:
            return {
                "mode": "fast",
                "depth": "shallow",
                "response_style": "direct",
                "priority": "high"
            }
        
        # Check if deep processing needed
        deep_needed = any(s.requires_deep_processing for s in signals.values())
        
        if deep_needed:
            return {
                "mode": "deep",
                "depth": "thorough",
                "response_style": "thoughtful",
                "priority": "normal"
            }
        
        return {
            "mode": "normal",
            "depth": "standard",
            "response_style": "balanced",
            "priority": "normal"
        }


# Alias for compatibility
AffectLayer = StandaloneAffectLayer