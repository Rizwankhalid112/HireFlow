import uuid

from django.db import models
from django.utils import timezone

from apps.cv_builder.models.cv_profile import CVProfile


class SuggestionSection(models.TextChoices):
    BULLETS = 'bullets', 'Work bullets'
    SUMMARY = 'summary', 'Professional summary'
    SKILLS = 'skills', 'Skills'
    PROJECT = 'project', 'Project key points'
    TITLE = 'title', 'Professional title'


class AISuggestionLog(models.Model):
    """One row per suggestion request.

    Three jobs, all of which need the row to exist from day one:

    - **Credits.** The monthly allowance is counted from these rows rather than a
      mutable counter, so a miscount is recoverable by recomputation and a
      refund is just not writing a row.
    - **Quality.** `accepted_index` is the honest signal for whether this feature
      works at all. Accept rate per section is the number to watch.
    - **Not repeating ourselves.** A rejected suggestion should not come back
      unchanged on the next regenerate.

    `suggestions` holds the raw validated model output. It is the user's own CV
    content, so it lives under the same retention as the rest of the profile —
    the CASCADE from CVProfile is deliberate.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='ai_suggestions')

    section = models.CharField(max_length=20, choices=SuggestionSection.choices)
    # Identifies the thing being written about (an experience or project id).
    # Null for whole-CV sections like summary.
    target_id = models.UUIDField(null=True, blank=True)

    # Hash of the built context, so an identical re-request is recognisable
    # without storing the prompt twice.
    input_digest = models.CharField(max_length=32, db_index=True)

    model = models.CharField(max_length=64)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    cached_tokens = models.IntegerField(default=0)

    suggestions = models.JSONField(default=dict)
    # Index into the returned variants, or null while nothing has been accepted.
    accepted_index = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'cv_ai_suggestion_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cv', '-created_at'], name='cv_ai_log_cv_recent_idx'),
        ]

    def __str__(self):
        return f'{self.section} for {self.cv_id} at {self.created_at:%Y-%m-%d %H:%M}'


def credits_used_this_period(cv):
    """Requests made in the current calendar month.

    Counted rather than decremented: a counter that drifts is unrecoverable,
    whereas a count can always be recomputed from the rows.
    """
    now = timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return AISuggestionLog.objects.filter(cv=cv, created_at__gte=start).count()
