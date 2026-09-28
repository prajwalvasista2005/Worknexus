import re
import string
from typing import Set

COMPANY_SUFFIXES = [
    r"\bpvt\b", r"\bltd\b", r"\bpvt\s+ltd\b", r"\bprivate\s+limited\b",
    r"\binc\b", r"\bcorp\b", r"\bcorporation\b", r"\bllc\b", r"\bllp\b",
    r"\bgmbh\b", r"\bco\b", r"\bcompany\b", r"\btechnologies\b",
    r"\btech\b", r"\bsolutions\b", r"\bservices\b", r"\bindia\b",
    r"\bconsulting\b", r"\bgroup\b", r"\binternational\b"
]
COMPANY_SUFFIX_PATTERN = re.compile(r"|".join(COMPANY_SUFFIXES), re.IGNORECASE)

TITLE_NOISE_TOKENS = [
    r"\bsr\b\.?", r"\bsenior\b", r"\bjr\b\.?", r"\bjunior\b",
    r"\blead\b", r"\bprincipal\b", r"\bstaff\b", r"\bassociate\b",
    r"\bentry\s+level\b", r"\bmid\s+level\b", r"\bexperienced\b",
    r"\bexpert\b", r"\bconsultant\b", r"\bintern\b", r"\btrainee\b"
]
TITLE_NOISE_PATTERN = re.compile(r"|".join(TITLE_NOISE_TOKENS), re.IGNORECASE)

LOCATION_MAP = {
    "bangalore": "bengaluru",
    "bengaluru": "bengaluru",
    "bombay": "mumbai",
    "mumbai": "mumbai",
    "delhi": "delhi ncr",
    "new delhi": "delhi ncr",
    "ncr": "delhi ncr",
    "gurgaon": "delhi ncr",
    "gurugram": "delhi ncr",
    "noida": "delhi ncr",
    "calcutta": "kolkata",
    "kolkata": "kolkata",
    "madras": "chennai",
    "chennai": "chennai",
    "hyderabad": "hyderabad",
    "secunderabad": "hyderabad",
    "pune": "pune",
    "ahmedabad": "ahmedabad"
}

def normalize_whitespace(text: str) -> str:
    """Collapses multiple whitespaces, tabs, newlines into a single space."""
    if not text:
        return ""
    return " ".join(text.strip().split())

def clean_text_for_comparison(text: str) -> str:
    """Normalizes text by removing non-alphanumeric punctuation and lowercasing."""
    if not text:
        return ""
    text = normalize_whitespace(text.lower())
    # Replace common punctuation with space to prevent glued words
    text = re.sub(r"[\/\-_,\.;:\(\)\[\]\|]", " ", text)
    # Remove remaining punctuation
    text = re.sub(r"[^\w\s]", "", text)
    return normalize_whitespace(text)

def normalize_company(company: str) -> str:
    """
    Normalizes company names for conservative comparison without modifying the original.
    Example: 'SAP India Pvt.Ltd' -> 'sap'
    """
    if not company:
        return ""
    cleaned = clean_text_for_comparison(company)
    cleaned = COMPANY_SUFFIX_PATTERN.sub(" ", cleaned)
    return normalize_whitespace(cleaned)

def normalize_title(title: str, strip_seniority: bool = False) -> str:
    """
    Normalizes job titles for comparison.
    Example: 'Senior Data Scientist (Python / SQL)' -> 'data scientist python sql'
    """
    if not title:
        return ""
    cleaned = clean_text_for_comparison(title)
    if strip_seniority:
        cleaned = TITLE_NOISE_PATTERN.sub(" ", cleaned)
    return normalize_whitespace(cleaned)

def normalize_location(location: str) -> str:
    """
    Normalizes Indian and global locations into standard metro names for comparison.
    Example: 'Bangalore/Bengaluru, Mumbai (All Areas)' -> 'bengaluru'
    """
    if not location:
        return ""
    cleaned = clean_text_for_comparison(location)
    
    if "remote" in cleaned or "wfh" in cleaned or "work from home" in cleaned:
        return "remote"
        
    for alias, standard in LOCATION_MAP.items():
        if alias in cleaned.split() or alias in cleaned:
            return standard
            
    return cleaned

def tokenize_and_clean(text: str) -> Set[str]:
    """Generates a set of normalized unique word tokens including short tech terms (ml, ai, ev)."""
    cleaned = clean_text_for_comparison(text)
    tokens = {word for word in cleaned.split() if len(word) >= 2}
    return tokens

def jaccard_similarity(text_a: str, text_b: str) -> float:
    """Computes token-level Jaccard similarity between two text snippets."""
    tokens_a = tokenize_and_clean(text_a)
    tokens_b = tokenize_and_clean(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return float(intersection) / float(union) if union > 0 else 0.0
