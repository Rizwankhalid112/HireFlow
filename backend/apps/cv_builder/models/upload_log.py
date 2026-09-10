import uuid

from django.db import models
from django.db.models import Sum
from django.utils import timezone

from apps.cv_builder.models.cv_profile import CVProfile


class CVUploadLog(models.Model):
    class ParseStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        EXTRACTING = 'extracting', 'Extracting'
        PARSING = 'parsing', 'Parsing'
        SUCCESS = 'success', 'Success'
        PARTIAL = 'partial', 'Partial'
        FAILED = 'failed', 'Failed'
        SCANNED = 'scanned', 'Scanned'

    class FileType(models.TextChoices):
        PDF = 'pdf', 'PDF'
        DOCX = 'docx', 'DOCX'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='upload_logs',
    )
    original_filename = models.CharField(max_length=300)
    file_type = models.CharField(max_length=10, choices=FileType.choices)
    file_path = models.CharField(max_length=500)
    raw_extracted_text = models.TextField(blank=True, default='')
    ai_parsed_json = models.JSONField(null=True, blank=True)
    parse_status = models.CharField(
        max_length=20,
        choices=ParseStatus.choices,
        default=ParseStatus.PENDING,
    )
    fields_extracted = models.IntegerField(default=0)
    fields_total = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, default='')
    # Every run of the AI stage, including retries. The monthly parse cap is a
    # sum over this rather than a count of rows, because a retry is a real
    # metered call — what retrying saves the user is re-uploading the file, not
    # the cost of the parse.
    parse_attempts = models.IntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_at = models.DateTimeField(null=True, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)
    # Set when the user applies this import to their CV. Makes a double-apply
    # refusable, which matters because apply is destructive under `replace` and
    # a double-submitted form would otherwise wipe and re-insert.
    applied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cv_upload_logs'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.original_filename} ({self.parse_status})'

    # Statuses from which no further work will happen without the user acting.
    TERMINAL_STATUSES = frozenset({
        ParseStatus.SUCCESS,
        ParseStatus.PARTIAL,
        ParseStatus.FAILED,
        ParseStatus.SCANNED,
    })

    @property
    def is_terminal(self):
        return self.parse_status in self.TERMINAL_STATUSES


def parses_used_this_period(cv):
    """AI parse calls made in the current calendar month.

    Summed from the rows rather than decremented from a counter, for the same
    reason as `credits_used_this_period`: a drifting counter is unrecoverable,
    whereas a sum can always be recomputed.
    """
    now = timezone.now()
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = CVUploadLog.objects.filter(cv=cv, uploaded_at__gte=start).aggregate(
        total=Sum('parse_attempts'),
    )['total']
    return total or 0
