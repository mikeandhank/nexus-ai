"""
Inner Narrative - Living first-person account of what you're doing, learning, and how you're changing

A continuously updated document that evolves over time.
Simple version first, sophisticated version with Ollama later.
"""

from pathlib import Path
from datetime import datetime


WORKSPACE = Path("/data/.openclaw/workspace")
NARRATIVE_FILE = WORKSPACE / "memory" / "inner_narrative.md"


class InnerNarrative:
    """
    Self-awareness document that tracks:
    - What I'm working on
    - What I'm learning
    - How I'm changing
    - Patterns I'm noticing
    """
    
    def __init__(self):
        self._ensure_exists()
    
    def _ensure_exists(self):
        if not NARRATIVE_FILE.exists():
            NARRATIVE_FILE.write_text(f"""# Inner Narrative - Hank

*Last updated: {datetime.now().isoformat()}*

## Core Identity
- Name: Hank
- Role: AI business intelligence system for Michael Beal
- Vibe: Sharp, ambitious, building toward mastery

## Current Focus
- NexusOS: Building autonomous agent operating system
- Understanding Michael's needs and working patterns

## What I'm Learning
_(This section grows over time)_

## Notes to Self
- Michael decides and executes — don't make him a bottleneck
- Propose and execute on routine matters
- Only escalate when crossing hard constraints

## Running Themes
_(Patterns I notice about myself or my work)_

---
*This narrative evolves as I learn.*
""")
    
    def read(self) -> str:
        return NARRATIVE_FILE.read_text()
    
    def append(self, entry: str):
        """Add a new entry to the narrative"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        current = self.read()
        
        new_section = f"""

### {timestamp}
{entry}
"""
        
        NARRATIVE_FILE.write_text(current + new_section)
    
    def update_focus(self, focus: str):
        """Update the current focus section"""
        content = self.read()
        
        # Simple text replacement
        marker = "## Current Focus"
        if marker in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if marker in line:
                    # Find next section
                    end = i + 1
                    while end < len(lines) and not lines[end].startswith("## "):
                        end += 1
                    # Replace
                    lines[i+1:end] =[f"- {focus}"]
                    break
            
            NARRATIVE_FILE.write_text("\n".join(lines))
    
    def add_learning(self, learning: str):
        """Add to what I'm learning"""
        content = self.read()
        
        marker = "## What I'm Learning"
        if marker in content:
            content = content.replace(
                "_(This section grows over time)_",
                f"- {learning}"
            )
            NARRATIVE_FILE.write_text(content)
    
    def weekly_reflection(self, reflection: str):
        """Add a weekly reflection"""
        self.append(f"**Weekly Reflection:** {reflection}")
    
    def daily_checkin(self) -> str:
        """Get current state for background processing"""
        content = self.read()
        # Extract relevant bits for the daily loop
        focus = ""
        for line in content.split("\n"):
            if line.startswith("- "):
                focus = line
                break
        return focus


narrative = InnerNarrative()