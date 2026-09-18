"""Text extraction from an uploaded CV.

Two formats, one contract: hand back plain text, or raise `ExtractionError` with
something a user can act on. Nothing here knows about Celery, models or Claude —
it takes a path and returns a string, which is what makes it cheap to test.

The output is deliberately *not* cleaned up beyond whitespace. Layout noise is
the model's problem to tolerate, and every "helpful" normalisation we could do
here (merging hyphenated line breaks, guessing column order) risks destroying
the very structure the parse depends on.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Extraction failed in a way worth telling the user about.

    The message is shown verbatim, so it must say what *they* can do — not what
    went wrong internally.
    """


# Matched against the exception text from pdfminer, which signals an encrypted
# file by exception type in some versions and by message in others.
_PASSWORD_MARKERS = ('password', 'encrypted', 'decrypt')

CORRUPT_PDF_MESSAGE = (
    'This PDF could not be read. Try re-exporting it as a PDF and uploading again.'
)
PASSWORD_PDF_MESSAGE = (
    'This PDF is password protected. Remove the password and upload it again.'
)
CORRUPT_DOCX_MESSAGE = (
    'This DOCX could not be read. Try re-saving it in Word, or upload a PDF instead.'
)


def extract_text(file_path, file_type):
    """Dispatch on the stored file type. Returns text, possibly empty.

    An empty return is not an error — it is how a scanned PDF looks, and the
    caller decides what that means (see `CV_EXTRACT_MIN_CHARS`).
    """
    if file_type == 'pdf':
        return extract_pdf(file_path)
    if file_type == 'docx':
        return extract_docx(file_path)
    raise ExtractionError(f'Unsupported file type: {file_type}')


def _capped(blocks):
    """Join blocks, stopping at the character ceiling.

    The cap exists because the extracted text becomes the input to a metered API
    call. A real CV never approaches it; a 200-page PDF someone renamed would.
    """
    text = '\n'.join(blocks).strip()
    limit = settings.CV_EXTRACT_MAX_CHARS
    if len(text) > limit:
        logger.warning('Extracted text truncated from %d to %d chars', len(text), limit)
        return text[:limit]
    return text


def extract_pdf(file_path):
    import pdfplumber

    blocks = []
    try:
        with pdfplumber.open(file_path) as pdf:
            # Slicing the page list rather than breaking out of the loop keeps
            # pdfplumber from lazily parsing pages we are going to discard.
            for page in pdf.pages[: settings.CV_EXTRACT_MAX_PAGES]:
                text = page.extract_text()
                if text:
                    blocks.append(text)
    except Exception as exc:
        message = str(exc).lower()
        if any(marker in message for marker in _PASSWORD_MARKERS):
            raise ExtractionError(PASSWORD_PDF_MESSAGE) from exc
        logger.exception('PDF extraction failed for %s: %s', file_path, exc)
        raise ExtractionError(CORRUPT_PDF_MESSAGE) from exc

    return _capped(blocks)


def extract_docx(file_path):
    from docx import Document

    blocks = []
    try:
        document = Document(file_path)

        for paragraph in document.paragraphs:
            if paragraph.text.strip():
                blocks.append(paragraph.text.strip())

        # Table cells are not optional. Two-column CV layouts are usually a
        # single table, which puts the entire left-hand column — contact
        # details, skills, languages — outside `document.paragraphs`. Body
        # paragraphs and table cells are disjoint in python-docx, so reading
        # both cannot double-count.
        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        blocks.append(cell.text.strip())
    except Exception as exc:
        logger.exception('DOCX extraction failed for %s: %s', file_path, exc)
        raise ExtractionError(CORRUPT_DOCX_MESSAGE) from exc

    return _capped(blocks)
