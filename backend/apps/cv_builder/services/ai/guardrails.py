"""Mechanical enforcement of the rules the prompts state.

The prompt is the first line of defence and this is the second. A prompt can be
talked past; a regex cannot. Everything here is deterministic, costs nothing, and
runs on every response before the user sees it.

The load-bearing check is `invented_numbers`. Numbers are simultaneously the
highest-value thing a bullet can carry, the thing a model most wants to invent,
and the easiest fabrication to detect — so they get a hard, mechanical gate
rather than trust.
"""

import logging
import re

from apps.cv_builder.models import SkillCanonical
from apps.cv_builder.services.metric_extractor import extract_metric

logger = logging.getLogger(__name__)

MAX_BULLET_CHARS = 220
MAX_SUMMARY_CHARS = 520
MAX_PROJECT_POINT_CHARS = 200
MIN_BULLET_CHARS = 10  # matches WorkBulletSerializer.validate_text

_NUMBER = re.compile(r'\d[\d,]*(?:\.\d+)?')

# Ordinals and small counts that appear in ordinary prose without being claims.
# "24/7" is deliberately absent — it is a real availability claim.
_HARMLESS = {'1', '2', '3'}


def _numerals(text):
    """Bare numerals in `text`, comma- and unit-stripped.

    '54%' -> '54', '$20k' -> '20', '3x faster' -> '3', '1,200' -> '1200'.
    """
    return {match.group(0).replace(',', '').rstrip('.') for match in _NUMBER.finditer(text)}


def invented_numbers(text, sources):
    """Numerals in `text` that appear nowhere in what the user gave us.

    Known limitation: this matches on the numeral alone, so if the user wrote
    "40 hours" and the model writes "40%", the 40 is considered sourced. Catching
    that needs semantic comparison. The check is deliberately conservative in the
    direction of the common failure — a number appearing from nowhere.
    """
    allowed = set()
    for source in sources:
        allowed |= _numerals(str(source))

    return sorted(_numerals(text) - allowed - _HARMLESS)


def ground_variants(variants, sources, max_chars, min_chars=0):
    """Drop any variant carrying an unsourced number or the wrong shape.

    Returns `(kept, rejected)`. Rejections are logged rather than raised: one bad
    variant out of three is a normal outcome, and the user is better served by
    the two good ones than by an error.
    """
    kept, rejected = [], []

    for variant in variants:
        text = (variant.text or '').strip()
        fabricated = invented_numbers(text, sources)

        if fabricated:
            rejected.append((text, f'unsourced numbers: {", ".join(fabricated)}'))
            continue
        if len(text) < min_chars:
            rejected.append((text, f'shorter than {min_chars} characters'))
            continue
        if len(text) > max_chars:
            rejected.append((text, f'longer than {max_chars} characters'))
            continue

        variant.text = text
        kept.append(variant)

    for text, reason in rejected:
        logger.warning('Dropped AI suggestion (%s): %s', reason, text[:120])

    return kept, rejected


def wants_a_metric(text):
    """True when the line carries no figure and would be stronger with one.

    Reuses the existing metric extractor rather than asking the model whether it
    used a number — deterministic, free, and already tested.
    """
    return extract_metric(text) is None


def lookup_canonical(name):
    """The canonical row for a skill name, or None.

    Exact canonical name first, and only then aliases. Putting both in one OR
    query makes the winner arbitrary when a name is simultaneously one skill's
    canonical name and a substring of another's alias — `Java` and `JavaScript`
    are exactly that pair — and losing that race silently relabels the skill.

    Shared by the suggestion path and the CV parse. It is deliberately one
    function: the ordering above is a bug fix, and a second copy of this logic
    would be a second chance to lose it.
    """
    name = (name or '').strip()
    if not name:
        return None

    canonical = SkillCanonical.objects.filter(canonical_name__iexact=name).first()
    if canonical is not None:
        return canonical

    # `icontains` on the JSON list is a substring search, so a hit is only a
    # candidate: 'script' matches 'ecmascript' without being an alias of
    # anything. Confirm against the actual alias list.
    lowered = name.lower()
    for row in SkillCanonical.objects.filter(aliases__icontains=name).order_by('-is_popular'):
        aliases = {alias.lower() for alias in (row.aliases or [])}
        if lowered in aliases:
            return row

    return None


def resolve_skills(candidates):
    """Match suggested skill names against the canonical table.

    The model proposes and this verifies. A canonical match carries the correct
    category and lets the skill be stored with `is_verified=True`; an unmatched
    name is still offered, but as freetext, exactly as a hand-typed skill would
    be. This is what keeps the verified/unverified distinction meaningful.
    """
    resolved = []

    for candidate in candidates:
        name = (candidate.name or '').strip()
        if not name:
            continue

        canonical = lookup_canonical(name)

        resolved.append({
            'name': canonical.canonical_name if canonical else name,
            'category': canonical.category if canonical else '',
            'canonical_id': str(canonical.id) if canonical else None,
            'is_verified': canonical is not None,
            'evidence': (candidate.evidence or '').strip(),
        })

    # De-duplicate on the resolved name, keeping the first (canonical matches
    # sort ahead because they arrive from the evidenced list first).
    seen, unique = set(), []
    for skill in resolved:
        key = skill['name'].lower()
        if key not in seen:
            seen.add(key)
            unique.append(skill)

    return unique


def drop_existing(skills, existing_names):
    """Remove anything already on the CV, matched case-insensitively."""
    existing = {name.lower() for name in existing_names}
    return [skill for skill in skills if skill['name'].lower() not in existing]
