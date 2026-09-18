"""Pull the quantified claim out of a bullet, if there is one.

Two callers, and the second is why the patterns have to be generous:

- `WorkBulletSerializer` stores the result on the bullet.
- `guardrails.wants_a_metric()` inverts it to decide whether the AI should ask
  the user for a figure. A missed metric there means **asking someone for a
  number their bullet already contains**, which reads as the assistant not
  having read what they wrote.

The original patterns required specific verbs (`reduced X by 40%`) or an exact
adjacency (`30 clients`), so ordinary lines like "Cut checkout latency by 40%"
and "over 30 enterprise clients" returned nothing.

Matching returns the **longest** match across all patterns rather than the first
pattern to hit, so "from 54% to 93%" wins over the bare "54%" inside it.
"""

import re

METRIC_PATTERNS = [
    # Ranges first in intent, though ordering no longer decides the winner.
    r'\d+(?:\.\d+)?%\s*(?:to|→|-|–)\s*\d+(?:\.\d+)?%',
    r'(?:from\s+)?\$?[\d,]+(?:\.\d+)?[kKmM]?\s*(?:to|→)\s*\$?[\d,]+(?:\.\d+)?[kKmM]?',
    # Any percentage. The omission that caused most of the misses.
    r'\d+(?:\.\d+)?%',
    # Money.
    r'\$[\d,]+(?:\.\d+)?\s*(?:k|K|M|bn|billion|million|thousand)?',
    # Multipliers.
    r'\d+(?:\.\d+)?x\b',
    # A count of something, allowing up to two words between the number and the
    # noun: "30 enterprise clients", "12 backend engineers".
    r'\d[\d,]*\+?\s+(?:\w+\s+){0,2}(?:'
    r'users?|clients?|customers?|companies|teams?|engineers?|developers?|'
    r'people|employees|students?|tests?|cases?|tickets?|records?|rows?|'
    r'transactions?|requests?|queries|endpoints?|services?|repos(?:itories)?|'
    r'countries|markets?|stores?|branches|projects?|articles?|models?'
    r')\b',
    # Durations, including a before/after pair — "800ms to 120ms" carries the
    # whole claim and should beat any single figure nested inside it.
    r'\d+(?:\.\d+)?\s*(?:ms|secs?|seconds?|mins?|minutes?|hours?|hrs?|days?|weeks?|months?)'
    r'\s*(?:to|→|-|–)\s*'
    r'\d+(?:\.\d+)?\s*(?:ms|secs?|seconds?|mins?|minutes?|hours?|hrs?|days?|weeks?|months?)\b',
    r'\d+\s*(?:ms|milliseconds?|seconds?|secs?|minutes?|mins?|hours?|days?|weeks?|months?|years?)\b',
    r'\d[\d,]*\+?\s*(?:per|a|an|/)\s*(?:second|minute|hour|day|week|month|year|sec|min|hr)\b',
]

_COMPILED = [re.compile(pattern, re.IGNORECASE) for pattern in METRIC_PATTERNS]


def extract_metric(text: str) -> str | None:
    """The most specific figure in `text`, or None.

    "Most specific" is approximated by length: a longer match carries more of
    the claim, so "from 54% to 93%" beats the "54%" nested inside it.
    """
    if not text:
        return None

    best = None
    for pattern in _COMPILED:
        for match in pattern.finditer(text):
            value = match.group().strip()
            if best is None or len(value) > len(best):
                best = value
    return best
