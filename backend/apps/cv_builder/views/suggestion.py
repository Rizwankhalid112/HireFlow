"""AI writing suggestions — one endpoint per section.

Per-section paths rather than one polymorphic endpoint: the request and response
bodies genuinely differ per section, and a single route would need a union type
on both sides of the wire for no benefit.

Every endpoint here is metered. `throttle_scope` is not decoration — these are
the only endpoints in the project that spend money per call, and an unthrottled
one is uncapped billing exposure.
"""

import logging

from django.conf import settings
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import (
    AISuggestionLog,
    CVProject,
    WorkExperience,
    credits_used_this_period,
)
from apps.cv_builder.services.ai import (
    SuggestionUnavailable,
    suggest_bullets,
    suggest_project_points,
    suggest_skills,
    suggest_summary,
    suggest_title,
)
from apps.cv_builder.utils import get_user_cv_profile

logger = logging.getLogger(__name__)

MAX_NOTE_CHARS = 1000


def _target_role(request, profile):
    """What the CV is being aimed at.

    Falls back to the `target_role` already on the account profile — the field
    exists, nothing else reads it, and it means the same thing here.
    """
    supplied = (request.data.get('target_role') or '').strip()
    if supplied:
        return supplied[:120]

    account_profile = getattr(request.user, 'profile', None)
    return (getattr(account_profile, 'target_role', '') or '').strip()


def _note(request):
    return (request.data.get('note') or '').strip()[:MAX_NOTE_CHARS]


class _SuggestionView(APIView):
    """Shared plumbing: auth, throttle scope, credits, error mapping."""

    permission_classes = [IsAuthenticated]
    throttle_scope = 'ai_suggest'

    def handle(self, request, profile):  # pragma: no cover - overridden
        raise NotImplementedError

    def post(self, request):
        profile = get_user_cv_profile(request.user)

        used = credits_used_this_period(profile)
        if used >= settings.AI_MONTHLY_CREDITS:
            return Response(
                {
                    'detail': (
                        'You have used all your AI suggestions for this month. '
                        'They reset on the 1st.'
                    ),
                    'credits': {'used': used, 'limit': settings.AI_MONTHLY_CREDITS},
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        try:
            payload = self.handle(request, profile)
        except SuggestionUnavailable as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        payload['credits'] = {
            'used': used + 1,
            'limit': settings.AI_MONTHLY_CREDITS,
            'remaining': max(settings.AI_MONTHLY_CREDITS - used - 1, 0),
        }
        return Response(payload)


class SuggestBulletsView(_SuggestionView):
    def handle(self, request, profile):
        experience = get_object_or_404(
            WorkExperience, pk=request.data.get('experience_id'), cv=profile,
        )
        return suggest_bullets(
            experience,
            note=_note(request),
            target_role=_target_role(request, profile),
        )


class SuggestSummaryView(_SuggestionView):
    def handle(self, request, profile):
        return suggest_summary(profile, target_role=_target_role(request, profile))


class SuggestSkillsView(_SuggestionView):
    def handle(self, request, profile):
        return suggest_skills(profile, target_role=_target_role(request, profile))


class SuggestProjectPointsView(_SuggestionView):
    def handle(self, request, profile):
        project = get_object_or_404(CVProject, pk=request.data.get('project_id'), cv=profile)
        return suggest_project_points(
            project,
            note=_note(request),
            target_role=_target_role(request, profile),
        )


class SuggestTitleView(_SuggestionView):
    def handle(self, request, profile):
        return suggest_title(profile, target_role=_target_role(request, profile))


class SuggestionAcceptView(APIView):
    """Record which variant the user took.

    Accept rate per section is the only honest measure of whether this feature
    works, and it cannot be reconstructed later — so it is recorded at the moment
    it happens, or not at all.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, log_id):
        profile = get_user_cv_profile(request.user)
        log = get_object_or_404(AISuggestionLog, pk=log_id, cv=profile)

        index = request.data.get('index')
        if index is not None:
            try:
                index = int(index)
            except (TypeError, ValueError):
                index = None

        log.accepted_index = index
        log.save(update_fields=['accepted_index'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class SuggestionCreditsView(APIView):
    """Remaining allowance, so the UI can show it before spending one."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        used = credits_used_this_period(profile)

        return Response({
            'used': used,
            'limit': settings.AI_MONTHLY_CREDITS,
            'remaining': max(settings.AI_MONTHLY_CREDITS - used, 0),
            'enabled': bool(settings.ANTHROPIC_API_KEY),
        })
