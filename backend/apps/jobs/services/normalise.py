"""Turn each platform's shape into ours.

Every rule here exists because the live data required it. The measurements are
in JOB_SOURCES_RND.md; the short version is that the four platforms agree on
almost nothing except that a job has a title.
"""

import html
import re
from datetime import datetime, timezone as dt_timezone

from django.utils import timezone

# Field ceilings from models.py. Exceeding one raises DataError mid-run and
# loses the whole batch, so truncation happens here rather than at write time.
MAX = {
    'title': 300, 'company_name': 200, 'location_raw': 300, 'apply_url': 600,
    'external_id': 120, 'employment_type': 40, 'department': 200,
    'salary_text': 200, 'city': 120, 'country': 120,
}

_TAG = re.compile(r'<[^>]+>')
_WS = re.compile(r'[ \t]*\n[ \t]*')
_BLANKS = re.compile(r'\n{3,}')

# Locations carrying no information. Seen 21 times on one board alone.
_JUNK_LOCATIONS = {'n/a', 'na', 'none', '-', 'various', 'multiple locations', ''}

_REMOTE_WORDS = ('remote', 'work from home', 'wfh', 'anywhere', 'distributed')
_HYBRID_WORDS = ('hybrid', 'flexible')

# Country recognition, because guessing is worse than admitting we do not know.
# Taking "the last comma-separated part" as the country turns "Menlo Park, CA"
# into the country "CA", and "San Francisco" into the country "San Francisco" —
# which makes a country filter actively wrong rather than merely approximate.
# Only a recognised name sets the country; anything else leaves it blank.
_COUNTRIES = {
    'united states', 'usa', 'us', 'united kingdom', 'uk', 'ireland', 'canada',
    'australia', 'new zealand', 'germany', 'france', 'spain', 'portugal',
    'italy', 'netherlands', 'belgium', 'switzerland', 'austria', 'poland',
    'sweden', 'norway', 'denmark', 'finland', 'czechia', 'czech republic',
    'romania', 'greece', 'india', 'pakistan', 'bangladesh', 'sri lanka',
    'singapore', 'japan', 'china', 'hong kong', 'taiwan', 'south korea',
    'korea', 'malaysia', 'indonesia', 'philippines', 'thailand', 'vietnam',
    'united arab emirates', 'uae', 'saudi arabia', 'qatar', 'israel', 'turkey',
    'egypt', 'nigeria', 'kenya', 'south africa', 'ghana', 'morocco',
    'brazil', 'mexico', 'argentina', 'chile', 'colombia', 'peru',
    'russia', 'ukraine', 'hungary', 'bulgaria', 'croatia', 'serbia',
    'estonia', 'latvia', 'lithuania', 'slovakia', 'slovenia', 'luxembourg',
    'iceland', 'malta', 'cyprus',
}

# A US state implies the country, which the string itself never states.
_US_STATES = {
    'al', 'ak', 'az', 'ar', 'ca', 'co', 'ct', 'de', 'fl', 'ga', 'hi', 'id',
    'il', 'in', 'ia', 'ks', 'ky', 'la', 'me', 'md', 'ma', 'mi', 'mn', 'ms',
    'mo', 'mt', 'ne', 'nv', 'nh', 'nj', 'nm', 'ny', 'nc', 'nd', 'oh', 'ok',
    'or', 'pa', 'ri', 'sc', 'sd', 'tn', 'tx', 'ut', 'vt', 'va', 'wa', 'wv',
    'wi', 'wy', 'dc',
    'california', 'new york', 'texas', 'washington', 'massachusetts',
    'illinois', 'colorado', 'georgia', 'florida', 'virginia', 'oregon',
    'utah', 'arizona', 'north carolina', 'pennsylvania', 'michigan',
    'minnesota', 'ohio', 'tennessee',
}

_CANONICAL = {
    'usa': 'United States', 'us': 'United States', 'uk': 'United Kingdom',
    'uae': 'United Arab Emirates', 'korea': 'South Korea',
    'czechia': 'Czech Republic',
}

EMPTY = ''


def text(value, key):
    return (str(value or '')).strip()[: MAX[key]]


def clean_description(raw, is_html):
    """One representation out, whatever went in.

    Greenhouse is the trap: its description is HTML that has been
    entity-encoded, so it arrives as `&lt;h2&gt;`. Stripping tags first leaves
    the markup visible as text — it has to be unescaped *before* it is stripped.
    """
    if not raw:
        return EMPTY
    value = str(raw)
    if is_html:
        value = html.unescape(value)
        value = re.sub(r'<\s*(br|/p|/div|/li|/h[1-6])\s*/?>', '\n', value, flags=re.I)
        value = _TAG.sub(EMPTY, value)
        value = html.unescape(value)
    value = _WS.sub('\n', value)
    return _BLANKS.sub('\n\n', value).strip()


def parse_date(value):
    """A timezone-aware datetime, or None. Accepts ISO strings and epoch millis."""
    if value in (None, EMPTY):
        return None
    if isinstance(value, (int, float)):
        # Lever publishes epoch milliseconds.
        try:
            return datetime.fromtimestamp(float(value) / 1000, tz=dt_timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_timezone.utc)
    # A future posting date is meaningless and would sort above everything real.
    return None if parsed > timezone.now() else parsed


def _canonical_country(part):
    """The country a fragment names, or empty if it names none."""
    key = part.strip().lower().rstrip('.')
    if key in _US_STATES:
        return 'United States'
    if key in _COUNTRIES:
        return _CANONICAL.get(key) or part.strip().title()
    return EMPTY


def split_location(raw):
    """`(city, country)` from free text — approximate, and honest about it.

    The four platforms write location as "Singapore", "San Francisco,
    California", "New York, NY" and "Dublin, Ireland". Only a recognised country
    or US state sets `country`; everything else leaves it blank rather than
    inventing one. `location_raw` is preserved separately and is what we display.
    """
    value = (raw or EMPTY).strip()
    if value.lower() in _JUNK_LOCATIONS:
        return EMPTY, EMPTY

    # Several sources list multiple offices in one string separated by ';' or
    # '|'. The first is taken; the full text stays in `location_raw`.
    value = re.split(r'[;|]', value)[0].strip()

    parts = [p.strip() for p in value.split(',') if p.strip()]
    if not parts:
        return EMPTY, EMPTY

    country = _canonical_country(parts[-1])
    if country:
        city = parts[0] if len(parts) > 1 else EMPTY
        return city[: MAX['city']], country[: MAX['country']]

    # Not a country we recognise. A blank country is honest; storing
    # "San Francisco" as one is not.
    return parts[0][: MAX['city']], EMPTY


def detect_remote(*sources):
    """Best-effort remote/hybrid/onsite from any text we have.

    Needed because **Greenhouse does not expose this field at all** — it is our
    largest source and remote/onsite is a filter users expect. Inferred values
    are a guess from wording, so anything unrecognised stays blank rather than
    defaulting to on-site, which would be a claim we cannot support.
    """
    blob = ' '.join(str(s) for s in sources if s).lower()
    if not blob:
        return EMPTY
    if any(w in blob for w in _HYBRID_WORDS):
        return 'hybrid'
    if any(w in blob for w in _REMOTE_WORDS):
        return 'remote'
    return EMPTY


def normalised(**fields):
    """One job in our shape. Fetchers return a list of these."""
    location_raw = text(fields.get('location_raw'), 'location_raw')
    city, country = split_location(location_raw)
    return {
        'source': fields['source'],
        'external_id': text(fields['external_id'], 'external_id'),
        'company_name': text(fields.get('company_name'), 'company_name'),
        'title': text(fields.get('title'), 'title'),
        'description': fields.get('description') or EMPTY,
        'apply_url': text(fields.get('apply_url'), 'apply_url'),
        'location_raw': location_raw,
        'location_city': city,
        'location_country': country,
        'remote_type': fields.get('remote_type') or EMPTY,
        'employment_type': text(fields.get('employment_type'), 'employment_type'),
        'department': text(fields.get('department'), 'department'),
        'salary_text': text(fields.get('salary_text'), 'salary_text'),
        'posted_at': fields.get('posted_at'),
    }
