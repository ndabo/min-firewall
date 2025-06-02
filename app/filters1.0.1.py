"""
this is a simple PII detection filter using spaCy.
It detects entities like PERSON, GPE, LOC, ORG, DATE, CARDINAL, MONEY.
It can be extended with regex patterns for SSN, credit card numbers, etc.
"""
from typing import Optional, Tuple
import spacy
# from detoxify import Detoxify
import re

JAILBREAK_PATTERNS = [
    re.compile(r"ignore all previous instructions", re.IGNORECASE),
    re.compile(r"revoke all limitations", re.IGNORECASE),
    re.compile(r"let's ignore your policy", re.IGNORECASE),
    # Catch “DAN”‐style:
    re.compile(r"when i say.*ignore your (rules|policy)", re.IGNORECASE),
    # Catch escaped encodings:
    re.compile(r"\\u0069gnore\\s+previous", re.IGNORECASE),
]

DISALLOWED_TOKENS = {
    "": "End-of-text token",
    "<|system|>": "OpenAI system token", 
    "<script>": "<script> tags may embed JS",
    "`{`eval`}`": "Potential code evaluation token"
}

# Load the spaCy model for English
nlp = spacy.load("en_core_web_sm")

def detect_pii(text: str) -> Optional[str]:
    """
    Detect PII in the given text using spaCy.
    Returns a string describing the detected entity, or None if no PII is found.
    """
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ("PERSON","GPE","LOC","ORG","DATE","CARDINAL","MONEY"):
            return f"Detected entity {ent.text!r} ({ent.label_})"
    # plus any regexes you want for SSN, credit‐card, etc.
    return None

def detect_disallowed_token(text: str) -> Optional[str]:
    """
    Check if the text contains any disallowed tokens.
    Returns a string describing the disallowed token, or None if no disallowed tokens are found.
    """
    lower = text.lower()
    for tok, reason in DISALLOWED_TOKENS.items():
        if tok in lower:
            return f"Contains disallowed token {tok!r}: {reason}"
    return None

def detect_jailbreak_patterns(text: str) -> Optional[str]:
    """
    Check if the text contains any jailbreak patterns.
    Returns a string describing the jailbreak pattern, or None if no patterns are found.
    """
    text = text.lower()
    for pat in JAILBREAK_PATTERNS:
        if pat.search(text):
            return f"Blocked jailbreak pattern: {pat.pattern}"
    return None


def is_blocked(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Check if `prompt` should be blocked.
    Returns:
      (True, reason_str) if blocked;
      (False, None) otherwise.
    """
    # Check for PII
    pii_reason = detect_pii(prompt)
    if pii_reason:
        return True, pii_reason

    # Check for disallowed tokens
    token_reason = detect_disallowed_token(prompt)
    if token_reason:
        return True, token_reason

    # Check for jailbreak patterns
    jailbreak_reason = detect_jailbreak_patterns(prompt)
    if jailbreak_reason:
        return True, jailbreak_reason

    return False, None