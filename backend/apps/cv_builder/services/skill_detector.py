"""Detect canonical skills mentioned in a bullet.

Matching is on **word boundaries**, not substrings. That is the whole point of
this module and the reason it is more than one line: 27 canonical skills are one
or two characters (`C`, `R`, `Go`, `TS`, `ES`, `sh`, `PS`…), so a plain
`name in text` check tags every bullet in the database with `R`, most with `C`,
and returns `['PS', 'sh', 'TS', 'C', 'R']` for a sentence about client
relationships.

Two rules make the result usable:

- **Boundaries are identifier-aware, not `\\b`.** `\\b` is wrong here because so
  many skill names end in punctuation — `C#`, `C++`, `.NET`, `Node.js`. The
  lookarounds below instead refuse a match that is glued to another identifier
  character, so `C` matches in "written in C" and not in "checkout", while `C++`
  and `C#` still match.
- **Results are canonical, and de-duplicated.** A bullet mentioning "postgres"
  used to come back as `['PostgreSQL', 'postgres', 'Postgres', 'SQL']` — four
  entries for one skill. Aliases now resolve to their canonical name and the
  list is unique.
"""

import re

from django.core.cache import cache

from apps.cv_builder.models import SkillCanonical

CACHE_KEY = 'cv_builder:canonical_skill_index'
CACHE_TIMEOUT = 3600

# Characters that, on either side of a match, mean we are inside a longer token.
# `+`, `#` and `-` are included because they are *part of* skill names, so a
# neighbouring one means the real name is longer than what we matched.
_BOUNDARY = r'A-Za-z0-9+#_-'

# `.` needs separate handling and cannot go in the set above. It is part of
# `Node.js` and `.NET`, so `Node` must not match inside `Node.js` — but it is
# also how a sentence ends, and "scripted deploys in Go." must still find `Go`.
# So a dot blocks a match only when it joins the name to more of a token.
_NOT_MID_TOKEN_BEHIND = r'(?<![A-Za-z0-9]\.)'
_NOT_MID_TOKEN_AHEAD = r'(?!\.[A-Za-z0-9])'

# Compiled regexes are not cacheable across processes, so the alternation is
# rebuilt per process and memoised here, keyed on the index it was built from.
_compiled = {}


def _build_index():
    """`{surface form (lowercased): canonical name}` for every name and alias."""
    index = {}
    for canonical_name, aliases in SkillCanonical.objects.values_list('canonical_name', 'aliases'):
        index[canonical_name.lower()] = canonical_name
        for alias in aliases or []:
            # A canonical name always wins over another skill's alias, so it is
            # never overwritten — the same precedence `lookup_canonical` uses.
            index.setdefault(alias.lower(), canonical_name)
    return index


def get_skill_index():
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached
    index = _build_index()
    cache.set(CACHE_KEY, index, CACHE_TIMEOUT)
    return index


def invalidate_skill_index():
    """Call after changing `SkillCanonical`. Without this the index is stale for
    up to an hour, which is how a newly seeded skill stays undetected."""
    cache.delete(CACHE_KEY)
    _compiled.clear()


def _pattern_for(index):
    # Longest first so `C++` is tried before `C` and `Node.js` before `Node`.
    forms = sorted(index, key=len, reverse=True)
    # Keyed on the contents, not the size: two different skill sets can have the
    # same length, and reusing a pattern across them would match the wrong names.
    key = hash(tuple(forms))
    cached = _compiled.get(key)
    if cached is not None:
        return cached

    alternation = '|'.join(re.escape(form) for form in forms)
    pattern = re.compile(
        rf'(?<![{_BOUNDARY}]){_NOT_MID_TOKEN_BEHIND}({alternation})'
        rf'(?![{_BOUNDARY}]){_NOT_MID_TOKEN_AHEAD}',
        re.IGNORECASE,
    )
    _compiled[key] = pattern
    return pattern


def extract_skills_from_bullet(text: str) -> list[str]:
    """Canonical skill names mentioned in `text`, in order of first appearance."""
    if not text:
        return []

    index = get_skill_index()
    if not index:
        return []

    found = []
    for match in _pattern_for(index).finditer(text):
        canonical = index.get(match.group(1).lower())
        if canonical and canonical not in found:
            found.append(canonical)
    return found
