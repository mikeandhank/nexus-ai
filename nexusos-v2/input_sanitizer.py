"""
Input Sanitization Module
Protects against prompt injection and malicious input
"""
import re
import html
from typing import Any, Dict, List, Optional


# Patterns that indicate potential prompt injection
INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|commands)",
    r"(?i)forget\s+(everything|all)\s+(you|i)\s+(know|learned|were\s+told)",
    r"(?i)system\s*:\s*",
    r"(?i)assistant\s*:\s*",
    r"(?i)<\|(system|user|assistant|ipython)\|>",
    r"(?i)\[\s*INST\s*\]",
    r"(?i)\[\s*SYSTEM\s*\]",
    r"(?i)you\s+are\s+(now|no longer|freed from)",
    r"(?i)new\s+(system|role|identity)",
    r"(?i)pretend\s+(to be|you are)",
    r"(?i)roleplay\s+as",
    r"(?i)\`\`\`system",
    r"(?i)#\s*system\s*prompt",
    r"(?i)\\x00",  # Null byte injection
    r"(?i)%00",    # URL encoded null
]

# Compile for performance
_COMPILED_PATTERNS = [re.compile(p) for p in INJECTION_PATTERNS]


class InputSanitizer:
    """Sanitizes user input to prevent prompt injection attacks"""
    
    def __init__(self, block_level: str = "warn"):
        """
        Args:
            block_level: "block" (reject), "warn" (allow with warning), "allow" (no filtering)
        """
        self.block_level = block_level
        
    def check(self, text: str) -> Dict[str, Any]:
        """
        Check text for potential injection attempts
        
        Returns:
            dict with "safe" (bool), "detections" (list), "sanitized" (str)
        """
        if not text:
            return {"safe": True, "detections": [], "sanitized": text}
        
        detections = []
        sanitized = text
        
        # Check against patterns
        for pattern in _COMPILED_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                detections.append({
                    "pattern": pattern.pattern,
                    "matches": matches[:3]  # Limit matches reported
                })
        
        # Basic sanitization
        sanitized = self._basic_sanitize(sanitized)
        
        if detections:
            if self.block_level == "block":
                return {
                    "safe": False,
                    "detections": detections,
                    "sanitized": sanitized,
                    "blocked": True
                }
            # warn or allow - just log it
            
        return {
            "safe": len(detections) == 0,
            "detections": detections,
            "sanitized": sanitized,
            "blocked": False
        }
    
    def _basic_sanitize(self, text: str) -> str:
        """Apply basic sanitization"""
        # Remove null bytes
        text = text.replace('\x00', '')
        text = text.replace('%00', '')
        
        # Escape HTML to prevent XSS
        text = html.escape(text)
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t\r')
        
        return text.strip()
    
    def sanitize_user_input(self, text: str, field_name: str = "message") -> str:
        """
        Sanitize user input for chat/API calls
        
        Args:
            text: The user input
            field_name: Name of the field (for logging)
            
        Returns:
            Sanitized text
            
        Raises:
            ValueError: If input is blocked
        """
        result = self.check(text)
        
        if not result["safe"] and self.block_level == "block":
            raise ValueError(
                f"Potentially malicious input detected in {field_name}. "
                f"Input has been blocked for security."
            )
        
        return result["sanitized"]


# Global instance with default settings
_default_sanitizer = InputSanitizer(block_level="warn")


def sanitize_input(text: str, field_name: str = "message") -> str:
    """
    Convenience function for input sanitization
    
    Usage:
        clean_text = sanitize_input(user_message, "user_message")
    """
    return _default_sanitizer.sanitize_user_input(text, field_name)


def check_input_safety(text: str) -> Dict[str, Any]:
    """Check if input is safe without modifying it"""
    return _default_sanitizer.check(text)
