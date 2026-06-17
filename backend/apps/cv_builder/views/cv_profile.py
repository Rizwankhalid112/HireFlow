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
