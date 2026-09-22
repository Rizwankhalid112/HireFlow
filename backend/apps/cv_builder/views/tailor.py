"""Tailoring — turn an accepted change list into a frozen CV, and keep it.

Costs no AI call. The analysis already happened when the match was run; this is
a text operation on documents we already hold, so it is neither metered nor
throttled. That matters to how the feature feels: once a user has matched a job,
re-tailoring and re-downloading are free.

The line this module holds, same as the CV import: **the master CV is never
written to.** A tailored CV is a snapshot beside it.
"""

import logging

from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import CVUploadLog, CVVersion, JobMatch
from apps.cv_builder.services import tailor
from apps.cv_builder.services.cv_sources import resolve_cv_text
from apps.cv_builder.services.pdf_renderer import RenderError
from apps.cv_builder.utils import get_user_cv_profile

logger = logging.getLogger(__name__)

DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

CANNOT_EDIT_PDF = (
    'We cannot edit a PDF without changing how it looks, so this one is not '
    'rewritten automatically. Use the change list below to update your CV, or '
    'upload the Word version and we will tailor it for you.'
)


def _safe_stem(text, fallback):
    keep = ''.join(c for c in (text or '') if c.isalnum() or c in ' -_').strip()
    return (keep or fallback).replace(' ', '-')[:60]


def serialize_version(version, include_detail=False):
    payload = {
        'id': str(version.id),
        'company': version.company,
        'job_title': version.job_title,
        'match_score': version.match_score,
        'source_type': version.source_type,
        'file_name': version.file_name,
        'change_count': version.change_count,
        'created_at': version.created_at,
        'expires_at': version.expires_at,
        'has_file': bool(version.file_blob),
    }
    if include_detail:
        payload['applied_rewrites'] = version.applied_rewrites
        payload['skipped_rewrites'] = version.skipped_rewrites
        payload['template_id'] = version.template_id
        # The posting it was written against — the reason the user opens this
        # months later is to revise for the interview, and the CV alone does not
        # tell them what the job asked for.
        payload['jd_text'] = version.job_match.jd_text if version.job_match else ''
        payload['cover_letter'] = version.job_match.cover_letter if version.job_match else ''
    return payload


class TailorPreviewView(APIView):
    """What would change, before anything does.

    Separate from the POST so the confirmation screen shows true occurrence
    counts and any rewrite that cannot be applied, rather than the user
    discovering either afterwards.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        profile = get_user_cv_profile(request.user)
        match = get_object_or_404(JobMatch, pk=pk, cv=profile, deleted_at__isnull=True)

        cv_text, upload = self._resolve(profile, match)
        planned, skipped = tailor.plan(cv_text, match.reworded_keywords)

        return Response({
            'planned': planned,
            'skipped': skipped,
            'can_edit_file': self._can_edit(match, upload),
            'notice': '' if self._can_edit(match, upload) else CANNOT_EDIT_PDF,
        })

    @staticmethod
    def _resolve(profile, match):
        if match.source_type == JobMatch.SourceType.UPLOAD and match.source_upload_id:
            upload = match.source_upload
            return (upload.raw_extracted_text if upload else ''), upload
        return resolve_cv_text(profile, 'profile')[0], None

    @staticmethod
    def _can_edit(match, upload):
        """A built CV always; an upload only when it is a DOCX we still hold."""
        if match.source_type != JobMatch.SourceType.UPLOAD:
            return True
        return bool(upload and upload.file_type == CVUploadLog.FileType.DOCX
                    and upload.file_blob)


class TailorView(APIView):
    """Accept a chosen set of rewrites and freeze the result."""

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        profile = get_user_cv_profile(request.user)
        match = get_object_or_404(JobMatch, pk=pk, cv=profile, deleted_at__isnull=True)

        chosen = self._chosen(request, match)
        if chosen is None:
            return Response(
                {'detail': 'Choose at least one change to apply.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cv_text, upload = TailorPreviewView._resolve(profile, match)
        planned, skipped = tailor.plan(cv_text, chosen)

        try:
            version = self._build(profile, match, upload, planned, skipped)
        except RenderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response(serialize_version(version, include_detail=True),
                        status=status.HTTP_201_CREATED)

    @staticmethod
    def _chosen(request, match):
        """The subset the user ticked, matched against what we actually offered.

        Taken from the stored analysis by key rather than trusted from the body:
        a client that posted its own `current_wording` could rewrite arbitrary
        text in someone's CV.
        """
        offered = {
            (r.get('keyword', ''), r.get('current_wording', '')): r
            for r in (match.reworded_keywords or [])
        }
        keys = request.data.get('accept')

        if keys is None:
            return list(offered.values()) or None

        picked = [
            offered[(k.get('keyword', ''), k.get('current_wording', ''))]
            for k in keys
            if (k.get('keyword', ''), k.get('current_wording', '')) in offered
        ]
        return picked or None

    def _build(self, profile, match, upload, planned, skipped):
        common = {
            'cv': profile,
            'job_match': match,
            'company': match.company,
            'job_title': match.job_title,
            'match_score': match.match_score,
            'source_type': match.source_type,
        }
        stem = _safe_stem(match.company or match.job_title, 'tailored-cv')

        if TailorPreviewView._can_edit(match, upload) and upload is not None:
            blob, applied, more_skipped = tailor.apply_to_docx(
                bytes(upload.file_blob), planned,
            )
            return CVVersion.objects.create(
                **common,
                file_blob=blob,
                file_name=f'{stem}-CV.docx',
                file_mime=DOCX_MIME,
                applied_rewrites=applied,
                skipped_rewrites=skipped + more_skipped,
            )

        if match.source_type == JobMatch.SourceType.UPLOAD:
            # A PDF. We keep the change list and produce no file — see the
            # notice on the preview endpoint.
            return CVVersion.objects.create(
                **common,
                applied_rewrites=[],
                skipped_rewrites=skipped + [
                    {**r, 'reason': CANNOT_EDIT_PDF} for r in planned
                ],
            )

        pdf, content_json, applied, more_skipped, template_id = tailor.apply_to_profile(
            profile, planned,
        )
        return CVVersion.objects.create(
            **common,
            content_json=content_json,
            template_id=template_id,
            file_blob=pdf,
            file_name=f'{stem}-CV.pdf',
            file_mime='application/pdf',
            applied_rewrites=applied,
            skipped_rewrites=skipped + more_skipped,
        )


class CVVersionListView(APIView):
    """The storage room.

    Ordered newest first and filtered to unexpired rows — the retention policy
    is enforced here as well as by the purge command, because the command can be
    late and a user should never open a CV the policy says is gone.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        versions = (
            CVVersion.objects.live()
            .filter(cv=profile)
            .only(
                'id', 'company', 'job_title', 'match_score', 'source_type',
                'file_name', 'applied_rewrites', 'created_at', 'expires_at',
            )
        )
        return Response({'versions': [serialize_version(v) for v in versions]})


class CVVersionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        profile = get_user_cv_profile(request.user)
        version = get_object_or_404(
            CVVersion.objects.live().select_related('job_match'), pk=pk, cv=profile,
        )
        return Response(serialize_version(version, include_detail=True))

    def delete(self, request, pk):
        profile = get_user_cv_profile(request.user)
        version = get_object_or_404(CVVersion.objects.live(), pk=pk, cv=profile)
        version.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CVVersionDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        profile = get_user_cv_profile(request.user)
        version = get_object_or_404(CVVersion.objects.live(), pk=pk, cv=profile)

        if not version.file_blob:
            return Response(
                {'detail': 'No file was produced for this one — see the change list.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        response = HttpResponse(bytes(version.file_blob), content_type=version.file_mime)
        response['Content-Disposition'] = f'attachment; filename="{version.file_name}"'
        return response
