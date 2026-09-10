"""The registry is the allowlist and the picker's source of truth, so an entry
that does not render is a broken gallery card, not a caught exception."""

import pytest
from django.template.loader import get_template as load_django_template

from apps.cv_builder.models.cv_profile import CVProfile
from apps.cv_builder.services.pdf_renderer import render_cv_pdf
from apps.cv_builder.templates_registry import (
    CV_TEMPLATES,
    DEFAULT_TEMPLATE_ID,
    public_registry,
    resolve_template_id,
    template_choices,
)


@pytest.mark.parametrize('template_id', sorted(CV_TEMPLATES))
def test_every_registry_entry_points_at_a_real_file(template_id):
    load_django_template(CV_TEMPLATES[template_id]['file'])


def test_exactly_two_templates_offer_a_photo():
    """The photo uploader only appears for these, and the context builder only
    passes a photo through for these. If the count drifts, one of the two has
    been changed without the other."""
    with_photo = [key for key, value in CV_TEMPLATES.items() if value['photo']]

    assert sorted(with_photo) == ['executive', 'modern']


def test_every_registry_id_is_a_valid_model_choice():
    model_choices = {value for value, _ in CVProfile._meta.get_field('template_id').choices}

    assert set(CV_TEMPLATES) == model_choices


def test_the_default_template_exists():
    assert DEFAULT_TEMPLATE_ID in CV_TEMPLATES


def test_choices_and_public_registry_agree_with_the_registry():
    assert {key for key, _ in template_choices()} == set(CV_TEMPLATES)
    assert {entry['id'] for entry in public_registry()} == set(CV_TEMPLATES)


def test_an_unknown_id_resolves_to_the_default():
    assert resolve_template_id('nope') == DEFAULT_TEMPLATE_ID
    assert resolve_template_id(None) == DEFAULT_TEMPLATE_ID
    assert resolve_template_id('classic') == 'classic'


@pytest.mark.slow
@pytest.mark.django_db
@pytest.mark.parametrize('template_id', sorted(CV_TEMPLATES))
def test_every_template_renders_with_realistic_data(sample_cv, template_id):
    pdf_bytes, page_count = render_cv_pdf(sample_cv, template_id)

    assert pdf_bytes.startswith(b'%PDF')
    assert page_count >= 1
