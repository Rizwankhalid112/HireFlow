import re

METRIC_PATTERNS = [
    r'\d+\+?\s*(?:tests?|cases?|tickets?)',
    r'\d+%\s*to\s*\d+%',
    r'reduced?\s+\w+\s+by\s+\d+%',
    r'\$[\d,]+(?:k|K|M)?',
    r'\d+x\s+(?:faster|improvement|reduction)',
    r'\d+\+?\s*(?:users?|clients?|companies)',
    r'\d+\+?\s*(?:engineers?|developers?)',
]


def extract_metric(text: str) -> str | None:
    for pattern in METRIC_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group()
    return None
