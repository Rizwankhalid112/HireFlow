"""Validation for the uploaded CV file.

This is the app's first user-supplied-file path other than the profile photo —
every other endpoint takes JSON — so this module is the whole security surface
of the upload feature. It follows the same principle as `photo.py`: decide what
a file is by looking inside it, never by trusting what the client called it.
"""

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.utils.text import get_valid_filename

from rest_framework import serializers

# The client sends these, so they are a hint and not a decision. Kept because a
# mismatch is worth rejecting early, before reading any bytes.
ALLOWED_CONTENT_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
}

# What the file actually is. A DOCX is a zip container, hence the zip magic.
PDF_MAGIC = b'%PDF-'
DOCX_MAGIC = b'PK\x03\x04'

# Enough for both signatures with room to spare, and small enough that a
# rejected file costs one read of a few bytes.
_SNIFF_BYTES = 8

MAX_FILENAME_LENGTH = 100


class CVUploadSerializer(serializers.Serializer):
    """Validates the file and reports which of our two types it really is.

    `validate_file` returns the file unchanged; the detected type is stashed on
    the serializer because DRF has nowhere else to put a derived value that is
    not a field the client sent.
    """

    file = serializers.FileField(required=True)

    def validate_file(self, uploaded):
        if uploaded.size == 0:
            raise serializers.ValidationError('That file is empty.')

        # nginx has its own body limit, but it is generous and applies to every
        # endpoint, so the real ceiling is enforced here.
        if uploaded.size > settings.CV_UPLOAD_MAX_BYTES:
            megabytes = settings.CV_UPLOAD_MAX_BYTES // (1024 * 1024)
            raise serializers.ValidationError(f'File must be {megabytes} MB or smaller.')

        head = uploaded.read(_SNIFF_BYTES)
        # Every later reader — the disk write, then pdfplumber — starts from the
        # beginning, so the cursor has to go back.
        uploaded.seek(0)

        if head.startswith(PDF_MAGIC):
            detected = 'pdf'
        elif head.startswith(DOCX_MAGIC):
            detected = 'docx'
        else:
            # The old binary .doc format starts with an OLE2 signature and is
            # the most common wrong upload, so it gets its own message rather
            # than the generic one.
            if head.startswith(b'\xd0\xcf\x11\xe0'):
                raise serializers.ValidationError(
                    'Old .doc files are not supported. Save as .docx or PDF and try again.'
                )
            raise serializers.ValidationError('Upload a PDF or DOCX file.')

        # A .docx signature is just a zip signature, so a renamed .zip or .xlsx
        # reaches here. python-docx will reject it during extraction, which is
        # the right place — this check only proves it is not a PDF.
        content_type = (uploaded.content_type or '').lower()
        if content_type and content_type not in ALLOWED_CONTENT_TYPES:
            raise serializers.ValidationError('Upload a PDF or DOCX file.')

        self.detected_type = detected
        return uploaded

    def safe_filename(self):
        """A filename that cannot escape the user's upload directory.

        `get_valid_filename` strips path separators, so `../../etc/passwd`
        becomes `etcpasswd`. Truncated because `original_filename` is 300 chars
        and a crafted name is otherwise unbounded.

        It *raises* rather than returning empty when a name reduces to nothing —
        `???` strips to `''` — so that is caught here. Letting it propagate
        would turn a odd filename into a 500 instead of a saved file.
        """
        raw = self.validated_data['file'].name or 'cv'
        try:
            safe = get_valid_filename(raw)[:MAX_FILENAME_LENGTH]
        except SuspiciousFileOperation:
            safe = ''
        return safe or 'cv'
