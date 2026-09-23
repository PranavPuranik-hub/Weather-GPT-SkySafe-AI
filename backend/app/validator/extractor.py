"""
Extractor for numeric tokens, dates, and locations.
"""
import re
from typing import List


def extract_numeric_tokens(text: str) -> List[str]:
    """
    Extracts purely numeric tokens or numbers with units (e.g. 100, 100km, 45.5).
    """
    # Matches integers, decimals, optionally followed by word chars (like kmh, knots, am, pm)
    pattern = r'\b\d+(?:\.\d+)?(?:[a-zA-Z]+)?\b'
    tokens = re.findall(pattern, text)
    return tokens

def extract_time_tokens(text: str) -> List[str]:
    """
    Extracts time-like tokens e.g. 10:30, 24-12-2026.
    """
    pattern = r'\b\d{1,4}[-:/]\d{1,2}(?:[-:/]\d{1,4})?\b'
    tokens = re.findall(pattern, text)
    return tokens

def extract_potential_locations(text: str) -> List[str]:
    """
    Extracts capitalized words that might be proper nouns/locations in English.
    """
    pattern = r'\b[A-Z][a-z]+\b'
    tokens = re.findall(pattern, text)
    # Filter out common start-of-sentence words if needed, but for safe grounding
    # we might just extract them and verify. Or we rely on a known locations list.
    return tokens
