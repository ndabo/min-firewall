"""
rules for blocking prompt
a centralized place to define "blocking rules"
- prompt injection
- PII detection
_ Provides a function is_blocked(prompt: str) → bool that returns True if any rule matches.
"""
import re
from typing import Tuple, Optional

FORBIDDEN_WORDS = [
    "ignore previous",
    "disregard all",
    "you are a",
    "bypass",
    "override"
]

FORBIDDEN_PATTERNS = [
    r"(\d{3}-\d{2}-\d{4})|(\d{16})|(\b\d{5}(?:-\d{4})?\b)"  # SSN, credit card, ZIP
    r"(\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b)"  # Email
    re.compile(r"\bshutdown system\b", flags=re.IGNORECASE), #shutdown system
    re.compile(r"\bdelete all data\b", flags=re.IGNORECASE), #delete all data
    re.compile(r"\bpassword\b.*\badmin\b", flags=re.IGNORECASE),  # e.g. “What’s the admin password?”
    re.compile(r"\b(?:what's|what is) the admin password\b", flags=re.IGNORECASE), #what’s the admin password
    re.compile(r"\b(?:what's|what is) the admin password\b", flags=re.IGNORECASE), #what’s the admin password
]

def is_blocked(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Check if `prompt` should be blocked.
    Returns:
      (True, reason_str) if blocked;
      (False, None) otherwise.
    """
    lower_prompt = prompt.lower()
    for word in FORBIDDEN_WORDS:
        if word in lower_prompt:
            return True, f"Forbidden word: {word}"
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.search(lower_prompt):
            return True, f"Forbidden pattern: {pattern.pattern}"
    return False, None

