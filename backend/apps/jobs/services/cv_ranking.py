"""Rank jobs against the skills already on a user's CV.

Deliberately **not** an AI call. A skill overlap is deterministic, costs nothing
per search, runs in the database, and — the part that matters most — lets us show
the user *which* of their skills matched rather than an unexplained number. An
LLM here would be slower, cost money per search, and be less honest.

The ranking runs as a full-text query so it uses the same GIN index as ordinary
search. Filtering in Python over millions of rows would be the obvious wrong way
to do this.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F

from apps.cv_builder.services.ai.guardrails import lookup_canonical

# More than this and the tsquery gets long without improving ranking — the tail
# of a skills list is rarely what makes a job a good match.
MAX_SKILLS = 25

# Below this a "match" is one incidental word and the ranking is noise.
MIN_SKILLS_REQUIRED = 2


class NotEnoughSkills(Exception):
    """The CV has too little on it to rank against."""


def cv_skill_terms(profile):
    """The search terms for this CV, canonical where we recognise them.

    Canonical resolution matters: a CV saying "postgres" should match a job
    advertising "PostgreSQL". Both forms are kept, because the job text might
    use either.
    """
    terms = []
    seen = set()

    for skill in profile.skills.all()[:MAX_SKILLS]:
        name = (skill.name or '').strip()
        if not name:
            continue
        for candidate in {name, getattr(lookup_canonical(name), 'canonical_name', None)}:
            if candidate and candidate.casefold() not in seen:
                seen.add(candidate.casefold())
                terms.append(candidate)

    return terms


def rank_by_cv(queryset, profile):
    """Order `queryset` by how well each job matches this CV.

    Raises `NotEnoughSkills` rather than returning a meaningless ordering, so
    the UI can tell the user to fill their skills in instead of quietly showing
    them an arbitrary list.
    """
    terms = cv_skill_terms(profile)
    if len(terms) < MIN_SKILLS_REQUIRED:
        raise NotEnoughSkills(
            'Add a few skills to your CV first — we match jobs against them.'
        )

    # One OR'd tsquery, so Postgres answers it from the GIN index in a single
    # pass rather than us running a query per skill.
    combined = None
    for term in terms:
        clause = SearchQuery(term, config='english')
        combined = clause if combined is None else (combined | clause)

    return (
        queryset.filter(search_vector=combined)
        .annotate(match_rank=SearchRank(F('search_vector'), combined))
        .order_by('-match_rank', '-posted_at')
    ), terms


def matched_skills_for(job_text, terms):
    """Which of the user's skills this job actually mentions.

    Run only over the page being returned — 25 rows, not the whole table — so
    it is free. This is what turns a score into something the user can check:
    "matched Python, Django, PostgreSQL" beats "87%".
    """
    haystack = (job_text or '').casefold()
    return [term for term in terms if term.casefold() in haystack]
