"""Prompt caching is a prefix match, so these prompts have to be constants.

A single interpolated value would make the system prefix unique per user, and
every request would silently pay full input price instead of the cache rate.
Nothing errors when that happens — which is exactly why it needs a test.
"""

import re

import pytest

from apps.cv_builder.services.ai import prompts

SECTIONS = ['bullets', 'summary', 'skills', 'project', 'title']


@pytest.mark.parametrize('section', SECTIONS)
def test_every_section_has_a_prompt(section):
    assert section in prompts.BY_SECTION
    assert prompts.BY_SECTION[section].strip()


@pytest.mark.parametrize('section', SECTIONS)
def test_prompts_carry_no_interpolation_placeholders(section):
    """`{}`-style placeholders or f-string leftovers mean somebody is about to
    format user data into the cached prefix."""
    text = prompts.BY_SECTION[section]

    assert not re.search(r'\{[a-z_]+\}', text), 'format placeholder in a cached prompt'
    assert '%s' not in text


@pytest.mark.parametrize('section', SECTIONS)
def test_prompts_are_long_enough_to_cache(section):
    """The minimum cacheable prefix is model-dependent and can be as high as
    ~1024 tokens. A prompt far below that silently never caches."""
    approx_tokens = len(prompts.BY_SECTION[section]) / 4
    assert approx_tokens > 200, f'{section} prompt may be too short to cache'


@pytest.mark.parametrize('section', ['bullets', 'summary', 'project'])
def test_generative_prompts_forbid_invention_explicitly(section):
    # Collapse whitespace first: the rule wraps across lines in the prompt
    # source, and the assertion is about the instruction, not the line breaks.
    text = ' '.join(prompts.BY_SECTION[section].lower().split())
    assert 'never introduce a fact' in text


def test_the_skills_prompt_separates_evidence_from_aspiration():
    text = prompts.SKILLS.lower()
    assert 'evidenced' in text and 'suggested_for_role' in text


def test_the_title_prompt_forbids_inflating_seniority():
    assert 'never inflate seniority' in prompts.TITLE.lower()


# --- the CV parse prompt ----------------------------------------------------
#
# Not in BY_SECTION: that maps the *suggestion* sections, and the parse is a
# different job with a different schema. It gets the same caching guarantee and
# the same anti-invention guarantee, so it gets the same tests.


def test_the_parse_prompt_carries_no_interpolation():
    assert not re.search(r'\{[a-z_]+\}', prompts.PARSE)
    assert '%s' not in prompts.PARSE


def test_the_parse_prompt_is_long_enough_to_cache():
    assert len(prompts.PARSE) / 4 > 200


def test_the_parse_prompt_forbids_invention():
    text = ' '.join(prompts.PARSE.lower().split())
    assert 'never introduce a fact' in text
    assert 'guessing is always wrong' in text


def test_the_parse_prompt_maps_by_content_not_heading():
    """The whole reason a model beats a regex parser here. If this instruction
    is ever dropped, unfamiliar headings start being ignored instead of mapped."""
    text = ' '.join(prompts.PARSE.lower().split())
    assert 'map by content, never by heading text' in text
    # A sample of the synonyms that must survive an edit.
    for heading in ['employment history', 'core competencies', 'career objective']:
        assert heading in text


def test_the_parse_prompt_covers_the_languages_trap():
    """Programming languages under a "Languages" heading is the single most
    damaging mapping error available, and it looks plausible enough to ship."""
    text = ' '.join(prompts.PARSE.lower().split())
    assert 'languages trap' in text
    assert 'must not go in' in text


def test_the_parse_prompt_requires_unmapped_sections_to_be_surfaced():
    text = ' '.join(prompts.PARSE.lower().split())
    assert 'unmapped_sections' in text
    assert 'do not drop them silently' in text


def test_the_parse_prompt_forbids_inventing_a_start_year():
    """The tempting shortcut is graduation year minus four."""
    text = ' '.join(prompts.PARSE.lower().split())
    assert 'never work backwards from a graduation year' in text
