"""The tailoring primitives.

These are the tests that matter most in the module: everything here runs against
a document the user will send to an employer, so the failure mode of a bug is
not a broken page, it is a wrong word on someone's CV.
"""

import io

import pytest
from docx import Document
from docx.shared import Pt, RGBColor

from apps.cv_builder.services import tailor


def rw(keyword, current, where='Skills'):
    return {'keyword': keyword, 'current_wording': current, 'where': where}


class TestPlanning:
    def test_a_wording_that_is_present_is_planned_with_its_count(self):
        text = 'Used Postgres here. Tuned Postgres there.'
        planned, skipped = tailor.plan(text, [rw('PostgreSQL', 'Postgres')])

        assert skipped == []
        assert planned[0]['occurrences'] == 2

    def test_a_wording_that_is_absent_is_skipped_with_a_reason(self):
        planned, skipped = tailor.plan('Python and Django.', [rw('Kubernetes', 'K8s')])

        assert planned == []
        assert 'does not appear' in skipped[0]['reason']

    def test_a_cv_already_using_the_target_wording_is_skipped(self):
        planned, skipped = tailor.plan('PostgreSQL', [rw('PostgreSQL', 'postgresql')])

        assert planned == []
        assert 'already uses' in skipped[0]['reason']

    def test_an_incomplete_suggestion_is_skipped_rather_than_guessed(self):
        planned, skipped = tailor.plan('anything', [rw('PostgreSQL', '')])

        assert planned == []
        assert skipped[0]['reason'] == 'Incomplete suggestion.'


class TestWordBoundaries:
    """The rule that stops this feature corrupting a CV."""

    def test_a_longer_word_containing_the_term_is_not_touched(self):
        # The failure this prevents: PostgreSQL -> PostgreSQLSQL.
        planned, skipped = tailor.plan('Expert in PostgreSQL.', [rw('PostgreSQL', 'Postgres')])

        assert planned == []

    def test_replacement_leaves_surrounding_words_alone(self):
        out = tailor.apply_to_text(
            'Postgres and PostgreSQL and Postgresql',
            [{'keyword': 'PostgreSQL', 'current_wording': 'Postgres'}],
        )

        assert out == 'PostgreSQL and PostgreSQL and Postgresql'

    @pytest.mark.parametrize('term,text', [
        ('C++', 'Wrote C++ for embedded work.'),
        ('.NET', 'Built .NET services.'),
        ('Node.js', 'Used Node.js in production.'),
        ('CI/CD', 'Owned CI/CD pipelines.'),
    ])
    def test_terms_containing_punctuation_are_found(self, term, text):
        """\\b would fail every one of these, which is why it is not used."""
        planned, _ = tailor.plan(text, [rw('X', term)])

        assert planned and planned[0]['occurrences'] == 1

    def test_matching_ignores_case_but_the_replacement_keeps_the_jobs_casing(self):
        out = tailor.apply_to_text(
            'postgres and POSTGRES',
            [{'keyword': 'PostgreSQL', 'current_wording': 'Postgres'}],
        )

        assert out == 'PostgreSQL and PostgreSQL'


def build_docx():
    """A document shaped like the ones that break naive implementations."""
    document = Document()

    para = document.add_paragraph()
    run = para.add_run('Optimised ')
    run.bold = True
    run.font.size = Pt(13)
    run.font.color.rgb = RGBColor(0xC0, 0x20, 0x20)
    italic = para.add_run('Postgres')
    italic.italic = True
    italic.font.size = Pt(11)
    para.add_run(' queries, and more Postgres tuning.')

    # Word splits a word across runs at any formatting boundary.
    split = document.add_paragraph()
    split.add_run('Deployed to Amazon ')
    bold = split.add_run('Web')
    bold.bold = True
    split.add_run(' Services daily.')

    # Two-column CV templates keep everything in table cells.
    table = document.add_table(rows=1, cols=1)
    table.rows[0].cells[0].paragraphs[0].add_run('Skills: Postgres, Docker')

    out = io.BytesIO()
    document.save(out)
    return out.getvalue()


class TestDocx:
    def test_the_users_own_file_is_edited_in_place(self):
        planned, _ = tailor.plan('Postgres', [rw('PostgreSQL', 'Postgres')])
        blob, applied, skipped = tailor.apply_to_docx(build_docx(), planned)

        text = '\n'.join(p.text for p in Document(io.BytesIO(blob)).paragraphs)
        assert 'PostgreSQL queries' in text
        assert 'Postgres ' not in text
        assert skipped == []

    def test_a_term_split_across_runs_is_still_replaced(self):
        """The case a run-by-run search misses."""
        planned, _ = tailor.plan('Amazon Web Services', [rw('AWS', 'Amazon Web Services')])
        blob, applied, _ = tailor.apply_to_docx(build_docx(), planned)

        text = '\n'.join(p.text for p in Document(io.BytesIO(blob)).paragraphs)
        assert 'Deployed to AWS daily.' in text
        assert applied[0]['occurrences'] == 1

    def test_formatting_survives_the_edit(self):
        """The whole promise of editing the file rather than rebuilding it."""
        planned, _ = tailor.plan('Postgres', [rw('PostgreSQL', 'Postgres')])
        blob, _, _ = tailor.apply_to_docx(build_docx(), planned)

        runs = Document(io.BytesIO(blob)).paragraphs[0].runs
        assert runs[0].bold is True
        assert runs[0].font.size == Pt(13)
        assert runs[0].font.color.rgb == RGBColor(0xC0, 0x20, 0x20)
        assert [r for r in runs if 'PostgreSQL' in r.text][0].italic is True

    def test_text_inside_tables_is_edited(self):
        planned, _ = tailor.plan('Postgres', [rw('PostgreSQL', 'Postgres')])
        blob, applied, _ = tailor.apply_to_docx(build_docx(), planned)

        cell = Document(io.BytesIO(blob)).tables[0].rows[0].cells[0]
        assert 'PostgreSQL, Docker' in cell.text

    def test_every_occurrence_in_a_paragraph_is_replaced(self):
        planned, _ = tailor.plan('Postgres Postgres', [rw('PostgreSQL', 'Postgres')])
        blob, applied, _ = tailor.apply_to_docx(build_docx(), planned)

        text = '\n'.join(p.text for p in Document(io.BytesIO(blob)).paragraphs)
        assert 'Postgres' not in text.replace('PostgreSQL', '')
        # Twice in the first paragraph, once in the table.
        assert applied[0]['occurrences'] == 3

    def test_a_term_absent_from_the_document_is_reported_not_silently_dropped(self):
        blob, applied, skipped = tailor.apply_to_docx(
            build_docx(),
            [{'keyword': 'Kubernetes', 'current_wording': 'K8s', 'where': 'Skills'}],
        )

        assert applied == []
        assert 'could not be located' in skipped[0]['reason']

    def test_an_untouched_document_still_opens(self):
        blob, applied, _ = tailor.apply_to_docx(build_docx(), [])

        assert applied == []
        assert Document(io.BytesIO(blob)).paragraphs


class TestOverlappingRewrites:
    """Two rewrites touching the same words would mangle a sentence."""

    def test_a_phrase_overlapping_a_term_is_refused(self):
        text = 'Optimised Postgres queries for the reporting endpoint.'
        planned, skipped = tailor.plan(text, [
            rw('PostgreSQL', 'Postgres'),
            rw('query optimisation', 'Optimised Postgres queries'),
        ])

        assert [p['current_wording'] for p in planned] == ['Postgres']
        assert 'Overlaps' in skipped[0]['reason']

    def test_the_surviving_rewrite_still_applies_cleanly(self):
        text = 'Optimised Postgres queries for the reporting endpoint.'
        planned, _ = tailor.plan(text, [
            rw('query optimisation', 'Optimised Postgres queries'),
            rw('PostgreSQL', 'Postgres'),
        ])

        assert tailor.apply_to_text(text, planned) == (
            'Optimised PostgreSQL queries for the reporting endpoint.'
        )

    def test_unrelated_rewrites_are_both_kept(self):
        planned, skipped = tailor.plan(
            'Postgres and Amazon Web Services.',
            [rw('PostgreSQL', 'Postgres'), rw('AWS', 'Amazon Web Services')],
        )

        assert len(planned) == 2
        assert skipped == []
