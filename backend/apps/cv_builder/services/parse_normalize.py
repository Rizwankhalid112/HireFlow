"""Turn a validated `ParsedCV` into something our models will actually accept.

The schema already guarantees shape and vocabulary — a `Literal` field cannot
hold a value our models reject. What it cannot guarantee is that a string fits
`max_length`, that a URL has a scheme, that a CGPA is inside a
`DecimalField(3, 2)`, or that a year is a year. That is this module's job.

Everything here is a pure function over plain data. No database writes, no model
instances, and the only queries are canonical-skill lookups — which is what
makes the rules cheap to test exhaustively, and they need to be: each one exists
because a real CV would otherwise fail the import with a `DataError`.

Two rules are worth calling out because they are policy, not plumbing:

- **A missing required field is a question, not a guess.** `start_year` is NOT
  NULL on both WorkExperience and Education, and real CVs routinely omit it —
  the usual education line prints only a graduation year. We flag the row and
  ask, rather than inferring "graduated 2019, so started 2015". Same rule the
  suggestions feature runs on: where a fact is missing, ask for it.
- **Programming languages under a "Languages" heading are moved to skills.** The
  prompt covers it, but a prompt is not a guarantee, and `Python (native
  speaker)` is the kind of error that looks plausible enough to get published.
"""

import re
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from apps.cv_builder.services.ai.guardrails import lookup_canonical
from apps.cv_builder.utils import normalize_profile_url

# Field ceilings, taken from the models. Exceeding one raises DataError at write
# time, which would fail an otherwise good import over a long company name.
MAX_LENGTHS = {
    'full_name': 100,
    'professional_title': 150,
    'email': 254,
    'phone': 30,
    'city': 100,
    'country': 100,
    'url': 200,
    'company_name': 200,
    'role_title': 200,
    'location': 200,
    'institution': 300,
    'field_of_study': 200,
    'skill_name': 100,
    'project_name': 200,
    'subtitle': 200,
    'certification_name': 300,
    'issuing_organization': 300,
    'language_name': 100,
    'heading': 200,
    'unmapped_content': 2000,
}

# WorkBulletSerializer.validate_text rejects anything shorter. Dropping the
# fragment keeps the role importable; letting it through would fail the role.
MIN_BULLET_CHARS = 10

# CVProjectSerializer.validate_tech_stack rejects more than this, which would
# fail the whole project over a long technology list.
MAX_TECH_STACK = 10

# EducationSerializer defaults an absent cgpa_scale to 4.0 and rejects a CGPA
# above its scale. A bare "9.1" is therefore unstorable unless we say what scale
# it is on. Above 4.0 the scale is effectively always 10 -- nobody reports a
# grade out of 20 -- so this infers the *scale* while leaving the grade the user
# wrote untouched, and says so in the notes.
ASSUMED_HIGH_SCALE = Decimal('10.0')

# Below the first, a "year" is OCR noise or a page number. Above the second, it
# is a typo. Both ends have been seen in real extracted text.
MIN_YEAR = 1950

# DecimalField(max_digits=3, decimal_places=2) tops out below 10, so a
# percentage grade cannot be stored as a CGPA. It is not one, either.
MAX_CGPA = Decimal('9.99')
MAX_CGPA_SCALE = Decimal('99.9')

_CGPA_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*(?:/|out of)\s*(\d+(?:\.\d+)?)', re.I)
_NUMBER_PATTERN = re.compile(r'\d+(?:\.\d+)?')


def _max_year():
    # Next year is allowed: an expected graduation date is legitimately future.
    return timezone.now().year + 1


def _text(value, key):
    """Strip and truncate. Truncation is silent by design — the alternative is
    failing an import over a long institution name, which helps nobody."""
    return (value or '').strip()[: MAX_LENGTHS[key]]


def _url(value):
    """CVs write `linkedin.com/in/name`. Django's URLValidator rejects that
    outright, so without this a large share of imports would lose their links."""
    cleaned = (value or '').strip()
    if not cleaned:
        return ''
    return (normalize_profile_url(cleaned) or '')[: MAX_LENGTHS['url']]


def _year(value):
    """A usable four-digit year, or None."""
    try:
        year = int(value or 0)
    except (TypeError, ValueError):
        return None
    if MIN_YEAR <= year <= _max_year():
        return year
    return None


def _month(value):
    try:
        month = int(value or 0)
    except (TypeError, ValueError):
        return None
    return month if 1 <= month <= 12 else None


def _date_range(start_year, start_month, end_year, end_month, is_current):
    """Sanity-check one date range and return it as a dict.

    Handles the two orderings that actually occur: a genuinely current role, and
    a reversed range from a CV that lists dates right-to-left or from an
    extractor that interleaved columns.
    """
    start_year = _year(start_year)
    end_year = _year(end_year)
    start_month = _month(start_month)
    end_month = _month(end_month)

    if is_current:
        # Matches what WorkExperienceSerializer.validate does anyway; doing it
        # here too keeps the diff preview honest about what will be saved.
        end_year = None
        end_month = None
    elif start_year and end_year and end_year < start_year:
        start_year, end_year = end_year, start_year
        start_month, end_month = end_month, start_month

    return {
        'start_year': start_year,
        'start_month': start_month,
        'end_year': end_year,
        'end_month': end_month,
        'is_current': bool(is_current),
    }


def parse_cgpa(raw):
    """`(cgpa, scale)` as Decimals, or `(None, None)`.

    Accepts "3.3/4.0", "3.72", "9.1 out of 10". Rejects a percentage and a
    classification like "First Class Honours" — a percentage is not a CGPA, and
    storing 85 in a field that maxes at 9.99 raises. Dropping it is better than
    mangling it: the user can type the real value in one keystroke.
    """
    text = (raw or '').strip()
    if not text:
        return None, None

    match = _CGPA_PATTERN.search(text)
    if match:
        value, scale = match.group(1), match.group(2)
    else:
        if '%' in text:
            return None, None
        found = _NUMBER_PATTERN.search(text)
        if not found:
            return None, None
        value, scale = found.group(0), None

    try:
        cgpa = Decimal(value)
        scale_value = Decimal(scale) if scale else None
    except InvalidOperation:
        return None, None

    if not (Decimal('0') < cgpa <= MAX_CGPA):
        return None, None
    if scale_value is not None and not (Decimal('0') < scale_value <= MAX_CGPA_SCALE):
        scale_value = None
    if scale_value is not None and cgpa > scale_value:
        # "4.0/3.3" is the fields swapped; a grade above its own scale is not
        # information we can act on.
        return None, None

    if scale_value is None and cgpa > Decimal('4.0'):
        scale_value = ASSUMED_HIGH_SCALE

    return cgpa, scale_value


def _personal(parsed):
    return {
        'full_name': _text(parsed.full_name, 'full_name'),
        'professional_title': _text(parsed.professional_title, 'professional_title'),
        'email': _text(parsed.email, 'email'),
        'phone': _text(parsed.phone, 'phone'),
        'city': _text(parsed.city, 'city'),
        'country': _text(parsed.country, 'country'),
        'linkedin_url': _url(parsed.linkedin_url),
        'github_url': _url(parsed.github_url),
        'portfolio_url': _url(parsed.portfolio_url),
        'summary': (parsed.summary or '').strip(),
    }


def _experiences(rows):
    out = []

    for row in rows:
        company = _text(row.company_name, 'company_name')
        title = _text(row.role_title, 'role_title')
        # Both are NOT NULL with no default. A row with neither is not a job,
        # it is a heading the model mistook for one.
        if not company and not title:
            continue

        bullets = [
            text.strip()
            for text in (row.bullets or [])
            if text and len(text.strip()) >= MIN_BULLET_CHARS
        ]

        entry = {
            'company_name': company,
            'role_title': title,
            'employment_type': row.employment_type or '',
            'location': _text(row.location, 'location'),
            'location_type': row.location_type or '',
            'bullets': bullets,
            **_date_range(
                row.start_year, row.start_month, row.end_year, row.end_month, row.is_current,
            ),
        }
        entry['needs_attention'] = _missing_required(entry, {'company_name', 'start_year'})
        out.append(entry)

    return out


def _education(rows):
    out = []

    for row in rows:
        institution = _text(row.institution, 'institution')
        if not institution:
            continue

        cgpa, scale = parse_cgpa(row.cgpa)
        dates = _date_range(row.start_year, 0, row.end_year, 0, row.is_current)

        entry = {
            'institution': institution,
            'degree_type': row.degree_type or '',
            'field_of_study': _text(row.field_of_study, 'field_of_study'),
            'cgpa': str(cgpa) if cgpa is not None else None,
            'cgpa_scale': str(scale) if scale is not None else None,
            'thesis_title': (row.thesis_title or '').strip(),
            'achievements': (row.achievements or '').strip(),
            'start_year': dates['start_year'],
            'end_year': dates['end_year'],
            'is_current': dates['is_current'],
        }
        # The single most common gap in a real CV: "BSc Computer Science, MIT,
        # 2019" states only the graduation year, and start_year is NOT NULL.
        entry['needs_attention'] = _missing_required(entry, {'start_year'})
        out.append(entry)

    return out


def _missing_required(entry, required):
    """Which NOT NULL fields this row cannot supply.

    Returned rather than filled in. The diff modal turns each name into one
    inline question, and the row does not import until it is answered — no
    fabrication, and no silently dropped degree.
    """
    return sorted(name for name in required if not entry.get(name))


def _skills(rows, extra=()):
    """Resolve, categorise and de-duplicate.

    `extra` carries skills rescued from the languages section (see
    `_split_languages`), so they go through the same resolution as any other.
    """
    seen = set()
    out = []

    for row in list(rows) + list(extra):
        name = _text(getattr(row, 'name', None) or getattr(row, 'language_name', ''), 'skill_name')
        if not name:
            continue

        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)

        canonical = lookup_canonical(name)
        out.append({
            # The canonical spelling wins: 'nodejs' and 'Node.js' should not
            # become two chips on the rendered CV.
            'name': canonical.canonical_name if canonical else name,
            'category': canonical.category if canonical else (getattr(row, 'category', '') or ''),
            'proficiency': getattr(row, 'proficiency', '') or '',
            'canonical_id': str(canonical.id) if canonical else None,
            'is_verified': canonical is not None,
        })

    return out


def _split_languages(rows):
    """Separate spoken languages from technical skills.

    The mechanical half of the "Languages" trap. `SkillCanonical` holds only
    technical skills — no spoken language is in it — so *any* canonical match
    means the entry is not a spoken language, whatever heading it sat under.

    Deliberately wider than "category == Languages": a CV listing PostgreSQL or
    Docker under a Languages heading is the same mistake as one listing Python,
    and the narrower check let those through as spoken languages.

    Deterministic, free, and it does not depend on the model having got it right.
    """
    spoken = []
    misfiled = []

    for row in rows:
        name = _text(row.language_name, 'language_name')
        if not name:
            continue

        if lookup_canonical(name) is not None:
            misfiled.append(row)
            continue

        spoken.append({
            'language_name': name,
            'proficiency': row.proficiency or '',
        })

    return spoken, misfiled


def _projects(rows):
    out = []
    for row in rows:
        name = _text(row.name, 'project_name')
        if not name:
            continue
        dates = _date_range(row.start_year, 0, row.end_year, 0, row.is_ongoing)
        out.append({
            'name': name,
            'subtitle': _text(row.subtitle, 'subtitle'),
            'description': (row.description or '').strip(),
            'tech_stack': [
                item.strip()[: MAX_LENGTHS['skill_name']]
                for item in (row.tech_stack or [])
                if item and item.strip()
            ][:MAX_TECH_STACK],
            'project_url': _url(row.project_url),
            'start_year': dates['start_year'],
            'end_year': dates['end_year'],
            'is_ongoing': dates['is_current'],
            'is_professional': bool(row.is_professional),
        })
    return out


def _certifications(rows):
    out = []
    for row in rows:
        name = _text(row.name, 'certification_name')
        if not name:
            continue
        out.append({
            'name': name,
            'issuing_organization': _text(row.issuing_organization, 'issuing_organization'),
            'issue_month': _month(row.issue_month),
            'issue_year': _year(row.issue_year),
            'expiry_year': _year(row.expiry_year),
            'credential_url': _url(row.credential_url),
        })
    return out


def _unmapped(rows):
    out = []
    for row in rows:
        heading = _text(row.heading, 'heading')
        content = (row.content or '').strip()[: MAX_LENGTHS['unmapped_content']]
        if heading or content:
            out.append({'heading': heading or 'Untitled section', 'content': content})
    return out


def normalize(parsed):
    """`ParsedCV` in, a JSON-serialisable dict out.

    The result is stored on the log and shown in the diff UI, so it must survive
    a round trip through `JSONField` — hence Decimals as strings and no model
    instances anywhere in it.
    """
    spoken_languages, misfiled = _split_languages(parsed.languages)

    payload = {
        'personal': _personal(parsed.personal),
        'work_experience': _experiences(parsed.work_experience),
        'education': _education(parsed.education),
        'skills': _skills(parsed.skills, extra=misfiled),
        'projects': _projects(parsed.projects),
        'certifications': _certifications(parsed.certifications),
        'languages': spoken_languages,
        'unmapped_sections': _unmapped(parsed.unmapped_sections),
        'notes': [],
    }

    assumed_scales = [
        entry['institution']
        for entry in payload['education']
        if entry['cgpa'] and entry['cgpa_scale'] == str(ASSUMED_HIGH_SCALE)
    ]
    if assumed_scales:
        payload['notes'].append(
            f"Assumed a 10-point grade scale for {', '.join(assumed_scales[:3])} — "
            f'the CV gave a grade but not the scale. Check it before saving.'
        )

    if misfiled:
        # Surfaced rather than done quietly: the user should be told we
        # overrode a section of their CV, even when we were right to.
        names = ', '.join(row.language_name for row in misfiled[:5])
        payload['notes'].append(
            f'Moved {names} from Languages into Skills — they look like '
            f'technologies, not spoken languages.'
        )

    return payload


def count_fields(payload):
    """`(extracted, total)` for the progress line in the UI.

    Counts sections that produced something plus the personal fields that came
    back filled, against a fixed denominator. It is a progress indicator, not an
    accounting figure — its only job is to tell the user roughly how much of
    their CV we understood.
    """
    personal = payload.get('personal', {})
    personal_fields = [
        'full_name', 'professional_title', 'email', 'phone',
        'city', 'country', 'linkedin_url', 'github_url', 'summary',
    ]
    extracted = sum(1 for name in personal_fields if personal.get(name))

    section_weights = {
        'work_experience': 4,
        'education': 3,
        'skills': 3,
        'projects': 1,
        'certifications': 1,
        'languages': 1,
    }
    for section, weight in section_weights.items():
        if payload.get(section):
            extracted += weight

    total = len(personal_fields) + sum(section_weights.values())
    return extracted, total
