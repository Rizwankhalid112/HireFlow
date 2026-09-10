"""Module 1 — score a CV against a pasted job description, and write a cover letter.

Three endpoints and one of them costs money, which is the whole shape of this
module: listing sources and reading past results are free, running a match is
metered and throttled.

Nothing here changes the user's CV. A match produces an opinion and a letter;
acting on either is a separate decision the user makes by hand. That is the same
line the CV import holds, and for the same reason — the risk in this feature is
writing a claim onto a document the user has to defend in an interview.
"""

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import JobMatch, job_matches_used_this_period
from apps.cv_builder.services.ai import (
    JobDescriptionTooShort,
    SuggestionUnavailable,
    match_job,
)
from apps.cv_builder.services.cv_sources import list_sources, resolve_cv_text
from apps.cv_builder.utils import get_user_cv_profile

logger = logging.getLogger(__name__)

CAP_MESSAGE = (
    'You have used all your job matches for this month. They reset on the 1st.'
)


def serialize(match, include_text=True):
    payload = {
        'id': str(match.id),
        'job_title': match.job_title,
        'company': match.company,
        'match_score': match.match_score,
        'summary': match.summary,
        'matched': match.matched_keywords,
        'reworded': match.reworded_keywords,
        'missing': match.missing_keywords,
        'source_type': match.source_type,
        'source_label': (
            match.source_upload.original_filename
            if match.source_upload else 'My HireFlow CV'
        ),
        'created_at': match.created_at,
    }
    if include_text:
        payload['cover_letter'] = match.cover_letter
        payload['jd_text'] = match.jd_text
    return payload


class CVSourceListView(APIView):
    """Which CVs this user can match against.

    Free, and called before every match, so it must stay a couple of queries.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        return Response({
            'sources': list_sources(profile),
            'matches': {
                'used': job_matches_used_this_period(profile),
                'limit': settings.AI_JOB_MATCH_MONTHLY_LIMIT,
            },
        })


class JobMatchView(APIView):
    """POST a job description, get keywords and a cover letter back."""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'job_match'

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        matches = JobMatch.objects.filter(
            cv=profile, deleted_at__isnull=True,
        ).select_related('source_upload')[:50]
        return Response([serialize(match, include_text=False) for match in matches])

    def post(self, request):
        profile = get_user_cv_profile(request.user)

        used = job_matches_used_this_period(profile)
        if used >= settings.AI_JOB_MATCH_MONTHLY_LIMIT:
            return Response(
                {
                    'detail': CAP_MESSAGE,
                    'matches': {'used': used, 'limit': settings.AI_JOB_MATCH_MONTHLY_LIMIT},
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        jd_text = (request.data.get('jd_text') or '').strip()
        source_type = request.data.get('source_type') or 'profile'
        upload_id = request.data.get('upload_id')

        try:
            cv_text, upload = resolve_cv_text(profile, source_type, upload_id)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result, usage = match_job(cv_text, jd_text)
        except JobDescriptionTooShort as exc:
            # A validation problem the user can fix, not a failure — 400 rather
            # than 503, and no row is written.
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except SuggestionUnavailable as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        match = JobMatch.objects.create(
            cv=profile,
            source_type=source_type,
            source_upload=upload,
            jd_text=jd_text,
            job_title=(result.job_title or '')[:200],
            company=(result.company or '')[:200],
            match_score=result.match_score,
            summary=result.summary,
            matched_keywords=[item.model_dump() for item in result.matched],
            reworded_keywords=[item.model_dump() for item in result.reworded],
            missing_keywords=[item.model_dump() for item in result.missing],
            cover_letter=result.cover_letter,
            model=settings.AI_MODEL,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_tokens=usage.cached_tokens,
        )

        payload = serialize(match)
        payload['matches'] = {
            'used': used + 1,
            'limit': settings.AI_JOB_MATCH_MONTHLY_LIMIT,
            'remaining': max(settings.AI_JOB_MATCH_MONTHLY_LIMIT - used - 1, 0),
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class JobMatchDetailView(APIView):
    """Read or delete one past match.

    Reading is free and unmetered on purpose: the cover letter written on Monday
    is wanted on Thursday, and charging for that would push people to copy it
    somewhere else immediately.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        profile = get_user_cv_profile(request.user)
        match = get_object_or_404(JobMatch, pk=pk, cv=profile, deleted_at__isnull=True)
        return Response(serialize(match))

    def delete(self, request, pk):
        profile = get_user_cv_profile(request.user)
        match = get_object_or_404(JobMatch, pk=pk, cv=profile, deleted_at__isnull=True)
        # Soft delete: the allowance is counted from rows, so removing one would
        # make "delete it and run again" an unlimited-usage bypass. The user
        # stops seeing it, which is what they asked for.
        match.deleted_at = timezone.now()
        match.save(update_fields=['deleted_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)
