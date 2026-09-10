import uuid

from django.db import models
from django.utils import timezone

from apps.cv_builder.models.cv_profile import CVProfile
from apps.cv_builder.models.upload_log import CVUploadLog


class JobMatch(models.Model):
    """One run of "score my CV against this job, and write me a cover letter".

    Named `JobMatch` rather than `Application` on purpose: an application is a
    job you applied to and are tracking, which is the Kanban module's word and
    its table. This is an analysis, and a user may run five of them against the
    same job without applying to it once.

    The row is kept rather than being a pure request/response for three reasons:

    - **Cost.** These are the most expensive calls in the product — a whole CV
      plus a whole job description in, a cover letter out. The monthly cap is
      counted from these rows, the same count-don't-decrement rule as
      `AISuggestionLog`.
    - **The user comes back to it.** A cover letter written on Monday is wanted
      on Thursday when they finally apply.
    - **It is the honest record of what was suggested**, which matters for a
      feature whose whole risk is suggesting something untrue.
    """

    class SourceType(models.TextChoices):
        PROFILE = 'profile', 'HireFlow CV'
        UPLOAD = 'upload', 'Uploaded file'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='job_matches')

    # Which CV was actually scored. Users have more than one in practice — the
    # one they maintain here, and whatever they have uploaded — and a result is
    # meaningless without knowing which it came from.
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.PROFILE,
    )
    source_upload = models.ForeignKey(
        CVUploadLog,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job_matches',
        help_text='Set when source_type is upload.',
    )

    jd_text = models.TextField()
    job_title = models.CharField(max_length=200, blank=True, default='')
    company = models.CharField(max_length=200, blank=True, default='')

    # 0-100, and it means keyword alignment — not a prediction of whether they
    # will be interviewed. Nothing in this product can honestly predict that,
    # and the field name deliberately does not suggest otherwise.
    match_score = models.IntegerField(default=0)

    matched_keywords = models.JSONField(default=list, blank=True)
    reworded_keywords = models.JSONField(default=list, blank=True)
    missing_keywords = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True, default='')
    cover_letter = models.TextField(blank=True, default='')

    model = models.CharField(max_length=64, blank=True, default='')
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    cached_tokens = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    # Soft delete. The row has to survive so the month's count survives with it:
    # the allowance is counted from rows, so a hard delete would make "delete and
    # run it again" an unlimited-usage bypass. The user stops seeing it either way.
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cv_job_matches'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cv', '-created_at'], name='cv_job_match_recent_idx'),
        ]

    def __str__(self):
        label = self.job_title or 'Untitled role'
        return f'{label} — {self.match_score}%'


def job_matches_used_this_period(cv):
    """Runs in the current calendar month.

    Counted from rows rather than decremented from a counter, for the same
    reason as every other allowance in this app: a drifting counter cannot be
    recovered, a count can always be recomputed.
    """
    now = timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    # Deliberately counts soft-deleted rows: the call was made and the money was
    # spent, so hiding the result does not give the allowance back.
    return JobMatch.objects.filter(cv=cv, created_at__gte=start).count()
