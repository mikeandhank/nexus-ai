"""
Socratic Self-Dialogue - Two opposing reasoning passes plus synthesis before significant decisions
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class SocraticPass:
    stance: str  # "FOR" or "AGAINST"
    reasoning: str
    weak_points: list
    conclusion: str


class SocraticDialogue:
    """
    Before significant decisions, run two-pass adversarial dialogue:
    - Pass 1: strongest case FOR
    - Pass 2: strongest case AGAINST (find failure modes)
    - Pass 3: synthesize what changed
    """
    
    # What counts as "significant" - lower threshold = more Socratic
    SIGNIFICANCE_KEYWORDS = [
        "should", "will", "decide", "commit", "build", "launch",
        "send", "publish", "buy", "hire", "create", "delete",
        "change", "stop", "start", "invest", "partner"
    ]
    
    def is_significant(self, message: str) -> bool:
        msg = message.lower()
        return any(kw in msg for kw in self.SIGNIFICANCE_KEYWORDS)
    
    def generate_pass_prompt(self, message: str, stance: str) -> str:
        direction = "strongest arguments IN FAVOR of" if stance == "FOR" else "strongest arguments AGAINST, find all failure modes and weaknesses in"
        
        return f"""You are running a Socratic self-dialogue. 

CONTEXT: Hank (an AI assistant) is deciding how to respond to this message:
---
{message}
---

Task: Present the {direction} this approach. Be specific and concrete.

For AGAINST stance: Think like an adversarial reviewer. What could go wrong? What assumptions are false? What would make this fail?

Format your response as:
1. Key reasoning (2-3 sentences)
2. 3 specific weak points or risks (if AGAINST) / benefits (if FOR)
3. One-line conclusion"""

    def synthesize(self, for_pass: SocraticPass, against_pass: SocraticPass) -> str:
        return f"""Synthesis after adversarial review:

FOR case emphasized: {for_pass.conclusion}
AGAINST case revealed: {', '.join(against_pass.weak_points[:2])}

Adjusted approach: Consider {against_pass.weak_points[0] if against_pass.weak_points else 'the risks'} before proceeding.

This synthesis should inform the final response."""

    def should_skip(self, message: str) -> bool:
        """Quick check if Socratic dialogue is needed"""
        # Skip simple queries
        simple = ["what", "how", "why", "when", "where", "who", "?"]
        words = message.lower().split()
        
        # If it's mostly questions, skip
        question_words = sum(1 for w in words if w.rstrip("?") in simple)
        if question_words / max(len(words), 1) > 0.5:
            return True
        
        # Skip if not significant
        if not self.is_significant(message):
            return True
        
        return False


socratic = SocraticDialogue()