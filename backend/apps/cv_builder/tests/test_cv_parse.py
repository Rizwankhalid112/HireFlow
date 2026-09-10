"""Stage 2: text to structured data, and the task that drives it.

`complete` is patched everywhere — a test suite must never spend money. What is
being asserted is the contract around the call, not the model's output quality,
which no unit test can check.

The load-bearing assertion in this file is the last one: **nothing on any parse
path writes to the CV.** That is the whole of the spec's overwrite protection,
and it is the kind of guarantee that decays silently once someone adds a
convenience save.
"""

from unittest.mock import patch

import pytest

from apps.cv_builder.models import CVUploadLog
from apps.cv_builder.services.ai.client import SuggestionUnavailable, Usage
from apps.cv_builder.tests import factories as f


@pytest.fixture
def upload_log(sample_cv):
    return CVUploadLog.objects.create(
        cv=sample_cv,
        original_filename='cv.pdf',
        file_type='pdf',
        file_path='cv_uploads/1/cv.pdf',
        raw_extracted_text='Ada Lovelace, Backend Engineer at Acme Corp since 2020.',
        parse_status=CVUploadLog.ParseStatus.EXTRACTING,
    )


def fake_complete(parsed):
    return lambda *args, **kwargs: (parsed, Usage(100, 200, 0))


@pytest.mark.django_db
class TestParseCvText:
    def test_the_cv_text_goes_in_messages_not_the_system_prompt(self, ai_enabled):
        """Prompt caching is a prefix match. One user's CV in the cached prefix
        means every request pays full input price, silently."""
        from apps.cv_builder.services.ai import parse

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv()),
        ) as mock:
            parse.parse_cv_text('SECRET CV TEXT')

        system_prompt, user_content = mock.call_args[0][0], mock.call_args[0][1]
        assert 'SECRET CV TEXT' not in system_prompt
        assert user_content == 'SECRET CV TEXT'

    def test_it_asks_for_a_bigger_ceiling_than_a_suggestion(self, ai_enabled, settings):
        """A truncated structured output arrives as parsed_output=None with
        nothing explaining why, so this is a correctness bound."""
        from apps.cv_builder.services.ai import parse

        settings.AI_PARSE_MAX_TOKENS = 8000
        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv()),
        ) as mock:
            parse.parse_cv_text('text')

        assert mock.call_args.kwargs['max_tokens'] == 8000

    def test_the_failure_message_is_about_a_file_not_about_text(self, ai_enabled):
        """"Your text is unchanged" is meaningless when the user uploaded a
        file and is watching a progress bar."""
        from apps.cv_builder.services.ai import parse

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv()),
        ) as mock:
            parse.parse_cv_text('text')

        message = mock.call_args.kwargs['unavailable_message']
        assert 'file is saved' in message

    def test_a_cv_with_no_roles_and_no_education_is_thin(self, ai_enabled):
        from apps.cv_builder.services.ai import parse

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv(skills=[f.skill()])),
        ):
            _payload, _usage, is_thin = parse.parse_cv_text('text')
        assert is_thin is True

    def test_a_cv_with_a_role_is_not_thin(self, ai_enabled):
        from apps.cv_builder.services.ai import parse

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv(work_experience=[f.experience()])),
        ):
            _payload, _usage, is_thin = parse.parse_cv_text('text')
        assert is_thin is False


@pytest.mark.django_db
class TestTheParseTask:
    def test_a_good_parse_lands_as_success(self, upload_log, ai_enabled):
        from apps.cv_builder.tasks import send_to_ai_parser

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv(work_experience=[f.experience()])),
        ):
            send_to_ai_parser(str(upload_log.id))

        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.SUCCESS
        assert upload_log.ai_parsed_json['work_experience']
        assert upload_log.parsed_at is not None

    def test_a_thin_parse_lands_as_partial_with_an_explanation(self, upload_log, ai_enabled):
        """`partial` no longer means "some of the JSON validated" — structured
        outputs make that unreachable. It means the layout defeated us."""
        from apps.cv_builder.tasks import send_to_ai_parser

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv()),
        ):
            send_to_ai_parser(str(upload_log.id))

        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.PARTIAL
        assert 'work experience or education' in upload_log.error_message

    def test_an_upstream_outage_lands_as_failed_with_a_retry_hint(self, upload_log, ai_enabled):
        from apps.cv_builder.tasks import send_to_ai_parser

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=SuggestionUnavailable('The CV reader is unavailable. Your file is saved.'),
        ):
            send_to_ai_parser(str(upload_log.id))

        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.FAILED
        assert 'file is saved' in upload_log.error_message

    def test_an_unexpected_error_does_not_kill_the_worker(self, upload_log, ai_enabled):
        from apps.cv_builder.tasks import send_to_ai_parser

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=ValueError('something nobody predicted'),
        ):
            send_to_ai_parser(str(upload_log.id))

        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.FAILED

    def test_the_attempt_is_counted_even_when_the_call_fails(self, upload_log, ai_enabled):
        """A call that times out still cost money. A cap that only counts
        successes is not a cap."""
        from apps.cv_builder.tasks import send_to_ai_parser

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=SuggestionUnavailable('down'),
        ):
            send_to_ai_parser(str(upload_log.id))

        upload_log.refresh_from_db()
        assert upload_log.parse_attempts == 1

    def test_a_vanished_log_is_not_an_error(self, sample_cv, ai_enabled):
        """The profile can be deleted while the task sits in the queue."""
        import uuid

        from apps.cv_builder.tasks import send_to_ai_parser

        send_to_ai_parser(str(uuid.uuid4()))  # must not raise

    def test_nothing_is_written_to_the_cv_on_any_parse_path(self, upload_log, ai_enabled):
        """The single most important assertion in this file. Parsed data reaches
        a CV only through an explicit apply — that is the overwrite protection,
        and it must not decay into "we save it for convenience"."""
        from apps.cv_builder.tasks import send_to_ai_parser

        cv = upload_log.cv
        before = {
            'experiences': cv.work_experiences.count(),
            'education': cv.education_entries.count(),
            'skills': cv.skills.count(),
            'full_name': cv.full_name,
        }

        with patch(
            'apps.cv_builder.services.ai.parse.complete',
            side_effect=fake_complete(f.parsed_cv(
                personal=f.personal(full_name='Someone Else Entirely'),
                work_experience=[f.experience(company_name='Ghost Corp')],
                education=[f.education(institution='Ghost University')],
                skills=[f.skill(name='Ghostscript')],
            )),
        ):
            send_to_ai_parser(str(upload_log.id))

        cv.refresh_from_db()
        assert cv.work_experiences.count() == before['experiences']
        assert cv.education_entries.count() == before['education']
        assert cv.skills.count() == before['skills']
        assert cv.full_name == before['full_name']


@pytest.mark.django_db
class TestTheStuckSweeper:
    @pytest.mark.parametrize('stuck_status', ['pending', 'extracting', 'parsing'])
    def test_a_stalled_upload_is_failed(self, upload_log, stuck_status, settings):
        """`pending` is included deliberately: the spec only names `extracting`,
        but a worker that is down never picks the task up at all."""
        from datetime import timedelta

        from django.utils import timezone

        from apps.cv_builder.tasks import fail_stuck_uploads

        CVUploadLog.objects.filter(pk=upload_log.pk).update(
            parse_status=stuck_status,
            uploaded_at=timezone.now() - timedelta(minutes=30),
        )
        fail_stuck_uploads()

        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.FAILED
        assert 'timed out' in upload_log.error_message

    def test_a_recent_upload_is_left_alone(self, upload_log):
        from apps.cv_builder.tasks import fail_stuck_uploads

        fail_stuck_uploads()
        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.EXTRACTING

    def test_a_finished_upload_is_never_touched(self, upload_log):
        from datetime import timedelta

        from django.utils import timezone

        from apps.cv_builder.tasks import fail_stuck_uploads

        CVUploadLog.objects.filter(pk=upload_log.pk).update(
            parse_status=CVUploadLog.ParseStatus.SUCCESS,
            uploaded_at=timezone.now() - timedelta(days=2),
        )
        fail_stuck_uploads()

        upload_log.refresh_from_db()
        assert upload_log.parse_status == CVUploadLog.ParseStatus.SUCCESS
