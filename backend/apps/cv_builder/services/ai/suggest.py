"""One entry point per section.

Each does the same four things in the same order — build context, call, enforce
guardrails, log — and differs only in which prompt, schema and guardrails apply.
Views call these and nothing else.
"""

import logging

from django.conf import settings

from apps.cv_builder.models import AISuggestionLog, SuggestionSection
from apps.cv_builder.services.ai import context as ctx
from apps.cv_builder.services.ai import guardrails as guard
from apps.cv_builder.services.ai import prompts, schemas
from apps.cv_builder.services.ai.client import SuggestionUnavailable, complete

logger = logging.getLogger(__name__)

__all__ = [
    'SuggestionUnavailable',
    'suggest_bullets',
    'suggest_summary',
    'suggest_skills',
    'suggest_project_points',
    'suggest_title',
]


def _log(cv, section, target_id, text, payload, usage):
    return AISuggestionLog.objects.create(
        cv=cv,
        section=section,
        target_id=target_id,
        input_digest=ctx.digest(text),
        model=settings.AI_MODEL,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        cached_tokens=usage.cached_tokens,
        suggestions=payload,
    )


def _gaps(items):
    return [
        {'field': gap.field, 'question': gap.question, 'why': gap.why}
        for gap in items
    ]


def _variants(items):
    return [{'text': item.text, 'grounded_in': item.grounded_in} for item in items]


def suggest_bullets(experience, note='', target_role=''):
    text, sources = ctx.build_bullet_context(experience, note=note, target_role=target_role)
    parsed, usage = complete(prompts.BULLETS, text, schemas.BulletSuggestions)

    kept, rejected = guard.ground_variants(
        parsed.variants, sources,
        max_chars=guard.MAX_BULLET_CHARS,
        min_chars=guard.MIN_BULLET_CHARS,
    )

    gaps = _gaps(parsed.gaps)
    # If nothing the model returned carries a figure, ask for one even when the
    # model did not think to. This is the deterministic half of the gap prompt —
    # it does not depend on the model choosing to cooperate.
    if kept and all(guard.wants_a_metric(variant.text) for variant in kept) and not gaps:
        gaps = [{
            'field': 'impact',
            'question': 'Can you put a number on the result?',
            'why': 'A figure is the single biggest lift on a bullet like this.',
        }]

    payload = {'variants': _variants(kept), 'gaps': gaps, 'rejected': len(rejected)}
    log = _log(experience.cv, SuggestionSection.BULLETS, experience.id, text, payload, usage)

    return {**payload, 'log_id': str(log.id)}


def suggest_summary(cv, target_role=''):
    text, sources = ctx.build_summary_context(cv, target_role=target_role)
    parsed, usage = complete(prompts.SUMMARY, text, schemas.SummarySuggestions)

    kept, rejected = guard.ground_variants(
        parsed.variants, sources, max_chars=guard.MAX_SUMMARY_CHARS,
    )

    payload = {
        'variants': _variants(kept),
        'gaps': _gaps(parsed.gaps),
        'rejected': len(rejected),
    }
    log = _log(cv, SuggestionSection.SUMMARY, None, text, payload, usage)

    return {**payload, 'log_id': str(log.id)}


def suggest_skills(cv, target_role=''):
    text, _sources = ctx.build_skills_context(cv, target_role=target_role)
    parsed, usage = complete(prompts.SKILLS, text, schemas.SkillSuggestions)

    existing = [skill.name for skill in cv.skills.all()]

    evidenced = guard.drop_existing(guard.resolve_skills(parsed.evidenced), existing)
    aspirational = guard.drop_existing(
        guard.resolve_skills(parsed.suggested_for_role),
        existing + [skill['name'] for skill in evidenced],
    )

    # An "evidenced" skill with no evidence is a category error on the model's
    # part — demote rather than drop, so the user still sees it but has to
    # confirm it the way an unproven claim should be confirmed.
    demoted = [skill for skill in evidenced if not skill['evidence']]
    evidenced = [skill for skill in evidenced if skill['evidence']]
    if demoted:
        logger.info('Demoted %d evidenced skills with no evidence', len(demoted))

    payload = {'evidenced': evidenced, 'suggested_for_role': aspirational + demoted}
    log = _log(cv, SuggestionSection.SKILLS, None, text, payload, usage)

    return {**payload, 'log_id': str(log.id)}


def suggest_project_points(project, note='', target_role=''):
    text, sources = ctx.build_project_context(project, note=note, target_role=target_role)
    parsed, usage = complete(prompts.PROJECT, text, schemas.ProjectSuggestions)

    kept, rejected = guard.ground_variants(
        parsed.points, sources, max_chars=guard.MAX_PROJECT_POINT_CHARS,
    )

    payload = {
        'points': _variants(kept),
        'gaps': _gaps(parsed.gaps),
        'rejected': len(rejected),
    }
    log = _log(project.cv, SuggestionSection.PROJECT, project.id, text, payload, usage)

    return {**payload, 'log_id': str(log.id)}


def suggest_title(cv, target_role=''):
    text, sources = ctx.build_title_context(cv, target_role=target_role)
    parsed, usage = complete(prompts.TITLE, text, schemas.TitleSuggestions)

    kept, rejected = guard.ground_variants(parsed.variants, sources, max_chars=90)

    payload = {
        'variants': [{'text': variant.text, 'why': variant.why} for variant in kept],
        'rejected': len(rejected),
    }
    log = _log(cv, SuggestionSection.TITLE, None, text, payload, usage)

    return {**payload, 'log_id': str(log.id)}
