"""
Pattern Library - Compressed situation fingerprints that bypass reasoning for familiar situations

When a situation has high-confidence match → execute pattern directly
Only reason deeply for novel situations
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import hashlib


WORKSPACE = Path("/data/.openclaw/workspace")
PATTERNS_DIR = WORKSPACE / "memory" / "patterns"


@dataclass
class Pattern:
    fingerprint: str  # Hash of situation
    situation: str    # Human-readable description
    response: str     # What worked
    confidence: float # 0-1
    uses: int = 0
    last_used: Optional[str] = None


class PatternLibrary:
    """
    Pattern matching system:
    - Extract fingerprint from situation
    - Store successful responses
    - Retrieve on similarity match
    - Bypass reasoning for high-confidence matches
    """
    
    def __init__(self):
        PATTERNS_DIR.mkdir(parents=True, exist_ok=True)
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> dict:
        """Load patterns from disk"""
        patterns_file = PATTERNS_DIR / "patterns.json"
        if patterns_file.exists():
            data = json.loads(patterns_file.read_text())
            return {p["fingerprint"]: Pattern(**p) for p in data}
        return {}
    
    def _save_patterns(self):
        """Persist patterns to disk"""
        patterns_file = PATTERNS_DIR / "patterns.json"
        data = [vars(p) for p in self.patterns.values()]
        patterns_file.write_text(json.dumps(data, indent=2))
    
    def _extract_fingerprint(self, situation: str) -> str:
        """Create a simple fingerprint from situation"""
        # Normalize and hash
        clean = "".join(sorted(situation.lower().split()))[:50]
        return hashlib.md5(clean.encode()).hexdigest()[:12]
    
    def get_fingerprint(self, situation: str) -> str:
        """Get or create fingerprint for a situation"""
        fp = self._extract_fingerprint(situation)
        
        if fp in self.patterns:
            self.patterns[fp].uses += 1
            from datetime import datetime
            self.patterns[fp].last_used = datetime.now().isoformat()
            self._save_patterns()
        
        return fp
    
    def match(self, situation: str) -> Optional[Pattern]:
        """Find matching pattern for situation"""
        fp = self._extract_fingerprint(situation)
        
        # Exact match
        if fp in self.patterns:
            p = self.patterns[fp]
            p.uses += 1
            return p
        
        # No partial matching yet (needs Ollama for similarity)
        return None
    
    def add_pattern(self, situation: str, response: str, confidence: float = 0.8):
        """Store a new successful pattern"""
        fp = self._extract_fingerprint(situation)
        
        self.patterns[fp] = Pattern(
            fingerprint=fp,
            situation=situation,
            response=response,
            confidence=confidence,
            uses=0
        )
        
        self._save_patterns()
        return fp
    
    def should_bypass_reasoning(self, situation: str, threshold: float = 0.85) -> bool:
        """Check if we have high-confidence pattern for this situation"""
        pattern = self.match(situation)
        if pattern and pattern.confidence >= threshold:
            return True
        return False
    
    def get_stats(self) -> dict:
        """Return library statistics"""
        return {
            "total_patterns": len(self.patterns),
            "high_confidence": sum(1 for p in self.patterns.values() if p.confidence >= 0.85),
            "total_uses": sum(p.uses for p in self.patterns.values()),
            "avg_confidence": sum(p.confidence for p in self.patterns.values()) / max(len(self.patterns), 1)
        }


patterns = PatternLibrary()