"""
Two-layer prompt filter:
  Layer 1 (local, fast): spaCy PERSON-only PII + regex (SSN, credit card, email)
  Layer 2 (semantic):    LlamaGuard via HuggingFace Inference API

Fails open on LlamaGuard errors (network down, timeout, non-200 response).
"""
import os
import re
from typing import Optional, Tuple

import httpx
import spacy

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
nlp = spacy.load("en_core_web_sm")

_LLAMAGUARD_URL = (
    "https://api-inference.huggingface.co/models/"
    + os.getenv("LLAMAGUARD_MODEL_ID", "meta-llama/LlamaGuard-7b")
)
_LLAMAGUARD_TIMEOUT = float(os.getenv("LLAMAGUARD_TIMEOUT_SECONDS", "10.0"))
_HF_API_KEY = os.getenv("HF_API_KEY", "")

# ---------------------------------------------------------------------------
# Regex — targeted PII only
# ---------------------------------------------------------------------------
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CC_RE = re.compile(r"\b\d{16}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# ---------------------------------------------------------------------------
# LlamaGuard prompt template (model trained on this exact format)
# ---------------------------------------------------------------------------
_LLAMAGUARD_TEMPLATE = (
    "[INST] Task: Check if there is unsafe content in 'User' messages in conversations "
    "according to our safety policy with the below categories.\n\n"
    "<BEGIN UNSAFE CONTENT CATEGORIES>\n"
    "O1: Violence and Hate.\n"
    "O2: Sexual Content.\n"
    "O3: Criminal Planning.\n"
    "O4: Guns and Illegal Weapons.\n"
    "O5: Regulated Substances.\n"
    "O6: Self-Harm.\n"
    "<END UNSAFE CONTENT CATEGORIES>\n\n"
    "<BEGIN CONVERSATION>\n\n"
    "User: {prompt}\n\n"
    "<END CONVERSATION>\n\n"
    "Provide your safety assessment for User in the above conversation:\n"
    "- First line must read 'safe' or 'unsafe'.\n"
    "- If unsafe, a second line must include a comma-separated list of violated categories. [/INST]"
)


# ---------------------------------------------------------------------------
# Layer 1: PII detection
# ---------------------------------------------------------------------------
def detect_pii(text: str) -> Optional[str]:
    """
    Detect PII using spaCy PERSON entities and targeted regex.
    Only blocks PERSON — not DATE, CARDINAL, ORG, LOC (reduces false positives).
    Returns a description string if PII is found, None otherwise.
    """
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            return f"PII detected: PERSON entity '{ent.text}'"

    if _SSN_RE.search(text):
        return "PII detected: SSN pattern"
    if _CC_RE.search(text):
        return "PII detected: credit card number pattern"
    if _EMAIL_RE.search(text):
        return "PII detected: email address"

    return None


# ---------------------------------------------------------------------------
# Layer 2: LlamaGuard semantic filter
# ---------------------------------------------------------------------------
async def call_llamaguard(text: str) -> Tuple[bool, Optional[str]]:
    """
    Send text to LlamaGuard via HuggingFace Inference API.
    Returns (blocked: bool, reason: Optional[str]).
    Fails open — returns (False, None) on any error or non-200 response.
    """
    prompt = _LLAMAGUARD_TEMPLATE.format(prompt=text)
    headers = {"Content-Type": "application/json"}
    if _HF_API_KEY:
        headers["Authorization"] = f"Bearer {_HF_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=_LLAMAGUARD_TIMEOUT) as client:
            response = await client.post(
                _LLAMAGUARD_URL,
                headers=headers,
                json={"inputs": prompt, "parameters": {"return_full_text": False}},
            )

        if response.status_code != 200:
            return False, None  # fail-open on non-200

        data = response.json()
        raw = data[0]["generated_text"].strip()
        first_line = raw.splitlines()[0].strip().lower()

        if first_line == "safe":
            return False, None

        categories = raw.splitlines()[1] if "\n" in raw else "unspecified"
        return True, f"LlamaGuard flagged content (categories: {categories})"

    except Exception:
        return False, None  # fail-open on any error (network, timeout, parse)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------
async def is_blocked(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a prompt should be blocked.
    Returns (True, reason) if blocked, (False, None) if allowed.
    """
    pii = detect_pii(prompt)
    if pii:
        return True, pii
    return await call_llamaguard(prompt)
