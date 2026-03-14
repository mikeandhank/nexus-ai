"""
Background Processing - Continuous loop that runs when idle

Now fully functional with Ollama integration.
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
    - Updates inner narrative with Ollama reflection
    - Generates hypotheses
    
    Uses local Ollama for private, fast processing.
    """
    
    def __init__(self):
        self._ensure_state()
        self._init_ollama()
    
    def _ensure_state(self):
        if not BACKGROUND_STATE.exists():
            BACKGROUND_STATE.write_text(json.dumps({
                "last_run": None,
                "next_run": None,
                "accumulated_observations": [],
                "hypotheses": []
            }))
    
    def _init_ollama(self):
        """Initialize Ollama client"""
        try:
            from .ollama_client import ollama
            self.ollama = ollama
            self.ollama_available = ollama.is_available()
        except Exception as e:
            print(f"[BackgroundProcessor] Ollama init failed: {e}")
            self.ollama = None
            self.ollama_available = False
    
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
            return "Ollama not available"
        
        return self._ollama_processing()
    
    def _ollama_processing(self) -> str:
        """Full processing when Ollama is available"""
        state = json.loads(BACKGROUND_STATE.read_text())
        
        # 1. Review recent activity
        observations = self._review_activity()
        
        if not observations:
            state["last_run"] = datetime.now().isoformat()
            BACKGROUND_STATE.write_text(json.dumps(state, indent=2))
            return "No new activity to process"
        
        # 2. Generate Ollama-powered reflection for inner narrative
        try:
            from .ollama_client import summarize_for_narrative
            reflection = summarize_for_narrative(observations)
            self._update_narrative_with_reflection(reflection)
        except Exception as e:
            print(f"[BackgroundProcessor] Ollama reflection failed: {e}")
            for obs in observations[:2]:
                self._update_narrative_simple(obs)
        
        # 3. Generate hypotheses
        hypotheses = self._generate_hypotheses(observations)
        
        # 4. Update state
        state["last_run"] = datetime.now().isoformat()
        state["accumulated_observations"].extend(observations[:3])
        state["hypotheses"].extend(hypotheses)
        state["accumulated_observations"] = state["accumulated_observations"][-20:]
        state["hypotheses"] = state["hypotheses"][-10:]
        
        BACKGROUND_STATE.write_text(json.dumps(state, indent=2))
        
        return f"Ollama processed {len(observations)} observations, generated {len(hypotheses)} hypotheses"
    
    def _review_activity(self) -> list:
        """Review recent activity from session logs"""
        observations = []
        memory_dir = WORKSPACE / "memory"
        
        # Check context file
        ctx_file = memory_dir / "working" / "context.md"
        if ctx_file.exists():
            ctx = ctx_file.read_text()
            if len(ctx) > 50:
                observations.append(ctx[:300])
        
        # Check for any pending files
        pending_file = memory_dir / "working" / "pending.json"
        if pending_file.exists():
            pending = json.loads(pending_file.read_text())
            if pending:
                observations.append(f"Pending tasks: {len(pending)} items")
        
        return observations
    
    def _update_narrative_with_reflection(self, reflection: str):
        """Update inner narrative with Ollama reflection"""
        try:
            from .inner_narrative import narrative
            narrative.append(f"Background reflection: {reflection}")
        except Exception as e:
            print(f"[BackgroundProcessor] Failed to update narrative: {e}")
    
    def _update_narrative_simple(self, observation: str):
        """Simple narrative update without Ollama"""
        try:
            from .inner_narrative import narrative
            narrative.append(f"Background review: {observation[:200]}")
        except:
            pass
    
    def _generate_hypotheses(self, observations: list) -> list:
        """Generate proactive hypotheses using Ollama"""
        hypotheses = []
        
        if not observations:
            return hypotheses
        
        # Simple hypothesis generation
        hypotheses.append({
            "text": f"Based on recent activity: {observations[0][:100]}...",
            "basis": "activity review",
            "timestamp": datetime.now().isoformat()
        })
        
        return hypotheses
    
    def quick_update(self):
        """Simple update without full processing"""
        state = json.loads(BACKGROUND_STATE.read_text())
        state["last_run"] = datetime.now().isoformat()
        BACKGROUND_STATE.write_text(json.dumps(state, indent=2))
    
    def run_once(self) -> str:
        """Force one background processing run"""
        return self.run() or "Background processing complete"
    
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