"""The cache key is content-addressed, and that is the whole point.

It used to hash content_updated_at, which is auto_now — so the template_id PATCH
the picker fires on every click invalidated the render for *every* template.
These tests fail silently if that regresses: nothing errors, the preview just
quietly costs a full render every time.
"""

import pytest

from apps.cv_builder.services.pdf_renderer import build_render_plan


@pytest.mark.django_db
def test_editing_content_changes_the_digest(sample_cv):
    before = build_render_plan(sample_cv, 'minimal').digest

    sample_cv.summary = f'{sample_cv.summary} Now with an extra sentence.'
    sample_cv.save()

    assert build_render_plan(sample_cv, 'minimal').digest != before


@pytest.mark.django_db
def test_a_template_patch_does_not_change_the_content_digest(sample_cv):
    """The bug this design exists to fix.

    Switching template bumps content_updated_at, but the *content* is identical,
    so the digest for a given template must not move.
    """
    before = build_render_plan(sample_cv, 'classic').digest

    sample_cv.template_id = 'compact'
    sample_cv.save()
    sample_cv.refresh_from_db()

    assert build_render_plan(sample_cv, 'classic').digest == before


@pytest.mark.django_db
def test_different_templates_get_different_keys(sample_cv):
    keys = {
        build_render_plan(sample_cv, template_id).cache_key
        for template_id in ('minimal', 'classic', 'compact')
    }
    assert len(keys) == 3


@pytest.mark.django_db
def test_switching_template_and_back_hits_the_cache(sample_cv):
    """Flipping through the gallery and returning must be free."""
    from apps.cv_builder.services import pdf_renderer

    calls = []
    original = pdf_renderer._render

    def counting_render(plan, cv):
        calls.append(plan.template_id)
        return original(plan, cv)

    pdf_renderer._render = counting_render
    try:
        pdf_renderer.render_cv_pdf(sample_cv, 'minimal')
        pdf_renderer.render_cv_pdf(sample_cv, 'classic')

        # The picker PATCHes template_id, which bumps content_updated_at.
        sample_cv.template_id = 'minimal'
        sample_cv.save()
        sample_cv.refresh_from_db()

        pdf_renderer.render_cv_pdf(sample_cv, 'minimal')
    finally:
        pdf_renderer._render = original

    assert calls == ['minimal', 'classic'], 'returning to a seen template re-rendered'


@pytest.mark.django_db
def test_an_unknown_template_shares_the_default_cache_entry(sample_cv):
    """resolve_template() falls back to the default, so the key must too —
    otherwise the same document is rendered twice under two keys."""
    assert (
        build_render_plan(sample_cv, 'no-such-template').cache_key
        == build_render_plan(sample_cv, 'minimal').cache_key
    )
