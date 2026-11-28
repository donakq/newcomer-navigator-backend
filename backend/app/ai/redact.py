"""Remove personal ID numbers before any text reaches the LLM (PRD: never send SSN, passport, SEVIS, I-94, A-number)."""

import re

MASK = "[REDACTED]"
PATTERNS = [
    re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b"),  # SSN
    re.compile(r"\bA-?\d{8,9}\b", re.IGNORECASE),  # USCIS A-number
    re.compile(r"\bN\d{10}\b", re.IGNORECASE),  # SEVIS ID
    re.compile(r"\b\d{9}[A-Z]\d\b|\b\d{11}\b"),  # I-94 admission number
    re.compile(r"\b(?:IOE|EAC|WAC|LIN|SRC|MSC|YSC)\d{10}\b", re.IGNORECASE),  # USCIS receipt number
    re.compile(r"\b[A-Z]\d{8}\b"),  # passport (common 1 letter + 8 digits)
]


def redact(text: str) -> str:
    for pattern in PATTERNS:
        text = pattern.sub(MASK, text)
    return text
