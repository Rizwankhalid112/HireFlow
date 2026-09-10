from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import CVProfile
from apps.cv_builder.serializers.cv_profile import (
    CVProfileCreateSerializer,
    CVProfileReadSerializer,
    CVProfileWriteSerializer,
)
from apps.cv_builder.services.completion import calculate_section_completion, compute_completion
from apps.cv_builder.services.reset_cv import ALL_SECTIONS, delete_cv, reset_cv
from apps.cv_builder.utils import get_user_cv_profile


class CVProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile, created = CVProfile.objects.get_or_create(
            user=request.user,
            defaults={'email': request.user.email},
        )
        serializer = CVProfileCreateSerializer(profile)
        status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(serializer.data, status=status_code)

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        return Response(CVProfileReadSerializer(profile).data)

    def put(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVProfileWriteSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        profile.refresh_from_db()
        return Response(CVProfileReadSerializer(profile).data)

    def patch(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVProfileWriteSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        profile.refresh_from_db()
        return Response(CVProfileReadSerializer(profile).data)

    def delete(self, request):
        """Remove the CV entirely. Everything hanging off it CASCADEs.

        The user can start again with POST. Kept separate from reset because
        they are different intentions: reset is "start this CV over", delete is
        "I do not want a CV here".
        """
        profile = get_user_cv_profile(request.user)
        delete_cv(profile)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CVProfileResetView(APIView):
    """Clear the CV without deleting it.

    `{"sections": ["work_experience", "skills"]}` clears just those; omitting
    `sections` clears everything. Section-level reset is the common case in
    practice — it is what you want after an import brought in the wrong roles.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = get_user_cv_profile(request.user)

        sections = request.data.get('sections')
        if sections is not None:
            if not isinstance(sections, list):
                return Response(
                    {'detail': 'sections must be a list.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            unknown = [s for s in sections if s not in ALL_SECTIONS]
            if unknown:
                return Response(
                    {'detail': f'Unknown section(s): {", ".join(map(str, unknown))}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not sections:
                return Response(
                    {'detail': 'Name at least one section, or omit sections to clear everything.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        cleared = reset_cv(profile, sections)
        profile.refresh_from_db()

        return Response({
            'cleared': cleared,
            'total_cleared': sum(cleared.values()),
            'profile': CVProfileReadSerializer(profile).data,
        })


class CVProfileCompletionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        score, is_complete = compute_completion(profile)
        return Response({
            'completion_score': score,
            'is_complete': is_complete,
            'section_completion': calculate_section_completion(profile),
        })
