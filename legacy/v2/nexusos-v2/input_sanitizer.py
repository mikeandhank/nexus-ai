"""
Input Sanitization Module
==========================
SQL injection, XSS protection, and input validation.
"""
import re
import html
import unicodedata
from typing import Optional, Dict, Tuple
from urllib.parse import urlparse


class InputSanitizer:
    """
    Comprehensive input sanitization for NexusOS.
    """
    
    SQL_DANGEROUS_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bEXEC\b|\bEXECUTE\b)",
        r"(--|\#|\/\*)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>.*?</iframe>",
        r"eval\s*\(",
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000) -> str:
        if not value or not isinstance(value, str):
            return ""
        value = unicodedata.normalize('NFKC', value)
        value = value[:max_length]
        value = html.escape(value)
        value = value.replace('\x00', '')
        return value.strip()
    
    @classmethod
    def sanitize_email(cls, email: str) -> Optional[str]:
        if not email:
            return None
        email = cls.sanitize_string(email, 254)
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return None
        return email.lower()
    
    @classmethod
    def sanitize_username(cls, username: str) -> Optional[str]:
        if not username:
            return None
        username = cls.sanitize_string(username, 50)
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return None
        return username
    
    @classmethod
    def sanitize_password(cls, password: str) -> Tuple[bool, Optional[str]]:
        if not password:
            return (False, "Password required")
        if len(password) < 8:
            return (False, "Password must be at least 8 characters")
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        if len(password) >= 12:
            return (True, None)
        elif sum([has_upper, has_lower, has_digit]) >= 2:
            return (True, None)
        return (False, "Password too weak")
    
    @classmethod
    def sanitize_url(cls, url: str) -> Optional[str]:
        if not url:
            return None
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return None
            return parsed.geturl()
        except Exception:
            return None
    
    @classmethod
    def sanitize_filename(cls, filename: str) -> Optional[str]:
        if not filename:
            return None
        filename = filename.replace('/', '').replace('\\', '')
        filename = filename.replace('\x00', '')
        if not re.match(r'^[a-zA-Z0-9_.-]+$', filename):
            return None
        dangerous = ['.exe', '.sh', '.bat', '.cmd', '.ps1', '.vbs']
        if any(filename.lower().endswith(ext) for ext in dangerous):
            return None
        return filename[:255]
    
    @classmethod
    def check_sql_injection(cls, value: str) -> bool:
        if not value:
            return False
        value_upper = value.upper()
        for pattern in cls.SQL_DANGEROUS_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def check_xss(cls, value: str) -> bool:
        if not value:
            return False
        value_lower = value.lower()
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        return False


# Quick functions
def sanitize(value: str, max_length: int = 1000) -> str:
    return InputSanitizer.sanitize_string(value, max_length)


def validate_email(email: str) -> Optional[str]:
    return InputSanitizer.sanitize_email(email)