import uuid

from django.db import models

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
    uploaded_at = models.DateTimeField(auto_now_add=True)
    extracted_at = models.DateTimeField(null=True, blank=True)
    parsed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'cv_upload_logs'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.original_filename} ({self.parse_status})'
