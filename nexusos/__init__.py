"""
NexusOS - Inner Life Architecture

Six capabilities for human-like autonomous reasoning:

1. Affect Layer - Weighted attention signals
2. Socratic Self-Dialogue - Adversarial reasoning
3. Pattern Library - Compressed experience
4. Inner Narrative - Self-awareness document
5. Theory of Mind - Operator model
6. Background Processing - Continuous thinking
"""

from .affect_layer import affect_layer, AffectLayer
from .socratic_dialogue import socratic, SocraticDialogue
from .pattern_library import patterns, PatternLibrary
from .inner_narrative import narrative, InnerNarrative
from .theory_of_mind import tom, TheoryOfMind
from .background_processor import background, BackgroundProcessor

__all__ = [
    "affect_layer", "AffectLayer",
    "socratic", "SocraticDialogue", 
    "patterns", "PatternLibrary",
    "narrative", "InnerNarrative",
    "tom", "TheoryOfMind",
    "background", "BackgroundProcessor"
]


def process_message(message: str, context: dict = None) -> dict:
    """
    Main entry point - run full inner life processing on a message.
    
    Returns:
        dict with:
        - directive: how to process (STANDARD, DEEP_ANALYSIS, etc.)
        - socratic_result: if significant decision
        - pattern_match: if familiar situation
        - tom_prediction: what Michael might want
    """
    context = context or {}
    
    # 1. Affect analysis
    signals = affect_layer.analyze(message, context)
    directive = affect_layer.get_processing_directive(signals)
    
    result = {
        "directive": directive,
        "signals": {k: {"weight": v.weight, "reason": v.reason} 
                   for k, v in signals.items()}
    }
    
    # 2. Check pattern library
    if patterns.should_bypass_reasoning(message):
        result["pattern_match"] = patterns.match(message).response
        result["bypassed_reasoning"] = True
    else:
        result["bypassed_reasoning"] = False
    
    # 3. Socratic dialogue for significant decisions
    if socratic.is_significant(message):
        result["socratic_needed"] = True
        # Note: actual passes run with model
        result["socratic_synthesis"] = "Run adversarial passes before responding"
    else:
        result["socratic_needed"] = False
    
    # 4. Theory of Mind prediction
    prediction = tom.predict(message)
    result["tom_prediction"] = {
        "answer": prediction.prediction,
        "confidence": prediction.confidence,
        "reasoning": prediction.reasoning
    }
    
    # 5. Update inner narrative if significant
    if directive in ["ADVERSARIAL_SELF_TEST", "MAX_EFFORT"]:
        narrative.append(f"Significant processing triggered by: {message[:100]}")
    
    # 6. Observe for Theory of Mind
    tom.observe(message, "", "pending")
    
    return result