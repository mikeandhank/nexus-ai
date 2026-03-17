"""
Input Sanitization Module
==========================
Enterprise-grade input validation and sanitization
SECURITY: SQL injection, XSS, command injection prevention
"""
import re
import html
import bleach
from typing import Any, Dict, List, Optional
from datetime import datetime


class InputSanitizer:
    """
    Comprehensive input sanitization for NexusOS
    """
    
    SQL_INJECTION_PATTERNS = [
        r"(\bunion\b.*\bselect\b)",
        r"(\bselect\b.*\bfrom\b)",
        r"(\binsert\b.*\binto\b)",
        r"(\bdelete\b.*\bfrom\b)",
        r"(\bupdate\b.*\bset\b)",
        r"(\bdrop\b.*\btable\b)",
        r"(--\s*$)",
        r"(;\s*drop\b)",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$]",
        r"\$\([^)]+\)",
        r"`[^`]+`",
        r"\|.*\w+",
    ]
    
    @classmethod
    def sanitize_sql(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError("Potential SQL injection detected")
        return value.replace("'", "''")
    
    @classmethod
    def sanitize_command(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        for pattern in cls.COMMAND_INJECTION_PATTERNS:
            if re.search(pattern, value):
                raise ValueError("Potential command injection detected")
        return value
    
    @classmethod
    def sanitize_html(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        allowed_tags = ['b', 'i', 'u', 'em', 'strong', 'a', 'p', 'br']
        allowed_attrs = {'a': ['href', 'title']}
        return bleach.clean(value, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    
    @classmethod
    def sanitize_filename(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Filename must be a string")
        value = value.replace('/', '').replace('\\', '')
        value = re.sub(r'[^\w\s\-.]', '', value)
        return value.replace('\x00', '')
    
    @classmethod
    def sanitize_email(cls, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError("Email must be a string")
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, value):
            raise ValueError("Invalid email format")
        return value.lower().strip()
    
    @classmethod
    def sanitize(cls, value: Any, field_type: str = "text") -> Any:
        if value is None:
            return None
        if field_type == "text":
            return str(value).strip()
        elif field_type == "email":
            return cls.sanitize_email(str(value))
        elif field_type == "filename":
            return cls.sanitize_filename(str(value))
        elif field_type == "sql":
            return cls.sanitize_sql(str(value))
        elif field_type == "html":
            return cls.sanitize_html(str(value))
        elif field_type == "command":
            return cls.sanitize_command(str(value))
        return str(value)


class RequestValidator:
    """Validate API requests"""
    
    @staticmethod
    def validate_user_registration(data: Dict) -> List[str]:
        errors = []
        try:
            InputSanitizer.sanitize_email(data.get('email', ''))
        except ValueError:
            errors.append("Invalid email format")
        if len(data.get('password', '')) < 12:
            errors.append("Password must be at least 12 characters")
        name = data.get('name', '').strip()
        if not name:
            errors.append("Name is required")
        return errors
    
    @staticmethod
    def validate_agent_creation(data: Dict) -> List[str]:
        errors = []
        name = data.get('name', '').strip()
        if not name:
            errors.append("Agent name is required")
        allowed_models = ['phi3', 'llama3', 'mistral', 'codellama']
        model = data.get('model', '')
        if model and model not in allowed_models:
            errors.append(f"Invalid model. Allowed: {allowed_models}")
        return errors
    
    @staticmethod
    def validate_chat_message(data: Dict) -> List[str]:
        errors = []
        message = data.get('message', '').strip()
        if not message:
            errors.append("Message is required")
        if len(message) > 10000:
            errors.append("Message too long (max 10000 chars)")
        return errors