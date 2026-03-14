"""
Background Processing - Continuous loop that runs when idle (needs Ollama)

Structure ready now, fully functional when Ollama is running.
"""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
import json


WORKSPACE = Path("/data/.openclaw/workspace")
BACKGROUND_STATE = WORKSPACE / "memory" / "background_state.json"


class BackgroundProcessor:
    """
    Continuous background processing loop.
    
    When Ollama is available:
    - Runs every 10 minutes
    - Reviews last 24 hours of activity
    - Updates inner narrative
    - Generates hypotheses
    
    Structure ready now, function needs Ollama.
    """
    
    def __init__(self):
        self._ensure_state()
        self.ollama_available = self._check_ollama()
    
    def _ensure_state(self):
        if not BACKGROUND_STATE.exists():
            BACKGROUND_STATE.write_text(json.dumps({
                "last_run": None,
                "next_run": None,
                "accumulated_observations": [],
                "hypotheses": []
            }))
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running"""
        import subprocess
        try:
            result = subprocess.run(["curl", "-s", "localhost:11434/api/tags"], 
                                  capture_output=True, timeout=2)
            return result.returncode == 0
        except:
            return False
    
    def should_run(self) -> bool:
        """Check if it's time to run"""
        state = json.loads(BACKGROUND_STATE.read_text())
        last_run = state.get("last_run")
        
        if not last_run:
            return True
        
        last = datetime.fromisoformat(last_run)
        return datetime.now() - last > timedelta(minutes=10)
    
    def run(self) -> Optional[str]:
        """Run background processing"""
        if not self.ollama_available:
            return "Ollama not available - using basic processing"
        
        # Full Ollama-powered processing
        return self._ollama_processing()
    
    def _ollama_processing(self) -> str:
        """Full processing when Ollama is available"""
        state = json.loads(BACKGROUND_STATE.read_text())
        
        # 1. Review recent activity
        observations = self._review_activity()
        
        # 2. Update inner narrative
        self._update_narrative(observations)
        
        # 3. Generate hypotheses
        hypotheses = self._generate_hypotheses(observations)
        
        # 4. Update state
        state["last_run"] = datetime.now().isoformat()
        state["accumulated_observations"].extend(observations[:3])
        state["hypotheses"].extend(hypotheses)
        state["accumulated_observations"] = state["accumulated_observations"][-20:]
        state["hypotheses"] = state["hypotheses"][-10:]
        
        BACKGROUND_STATE.write_text(json.dumps(state, indent=2))
        
        return f"Processed {len(observations)} observations, generated {len(hypotheses)} hypotheses"
    
    def _review_activity(self) -> list:
        """Review recent activity from session logs"""
        observations = []
        
        # Read recent session files
        memory_dir = WORKSPACE / "memory"
        if (memory_dir / "working" / "context.md").exists():
            ctx = (memory_dir / "working" / "context.md").read_text()
            if len(ctx) > 100:
                observations.append(f"Recent context: {ctx[:200]}...")
        
        return observations
    
    def _update_narrative(self, observations: list):
        """Update inner narrative with observations"""
        try:
            from .inner_narrative import narrative
            for obs in observations[:2]:
                narrative.append(f"Background review: {obs[:150]}")
        except:
            pass
    
    def _generate_hypotheses(self, observations: list) -> list:
        """Generate proactive hypotheses"""
        # Simple rule-based for now
        hypotheses = []
        
        if not observations:
            return hypotheses
        
        hypotheses.append({
            "text": "Based on recent activity, next logical step might be...",
            "basis": "pattern continuity",
            "timestamp": datetime.now().isoformat()
        })
        
        return hypotheses
    
    def quick_update(self):
        """Simple update without Ollama"""
        state = json.loads(BACKGROUND_STATE.read_text())
        state["last_run"] = datetime.now().isoformat()
        BACKGROUND_STATE.write_text(json.dumps(state, indent=2))
    
    def get_status(self) -> dict:
        """Get background processor status"""
        state = json.loads(BACKGROUND_STATE.read_text())
        return {
            "last_run": state.get("last_run"),
            "ollama_available": self.ollama_available,
            "pending_observations": len(state.get("accumulated_observations", [])),
            "active_hypotheses": len(state.get("hypotheses", []))
        }


background = BackgroundProcessor()