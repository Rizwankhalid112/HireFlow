from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import Education
from apps.cv_builder.serializers.education import EducationSerializer
from apps.cv_builder.utils import get_user_cv_profile, reorder_owned_items


class EducationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        entries = Education.objects.filter(cv=profile)
        return Response(EducationSerializer(entries, many=True).data)

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = EducationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save(cv=profile)
        return Response(EducationSerializer(entry).data, status=status.HTTP_201_CREATED)


class EducationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return Education.objects.get(id=pk, cv__user=request.user)
        except Education.DoesNotExist:
            raise NotFound('Education entry not found.')

    def put(self, request, pk):
        entry = self.get_object(request, pk)
        serializer = EducationSerializer(entry, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(EducationSerializer(entry).data)

    def delete(self, request, pk):
        entry = self.get_object(request, pk)
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class EducationReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ValidationError({'ordered_ids': 'A non-empty list of IDs is required.'})

        try:
            reorder_owned_items(Education, ordered_ids, {'cv__user': request.user})
        except ValueError as exc:
            raise ValidationError({'ordered_ids': str(exc)}) from exc

        profile = get_user_cv_profile(request.user)
        entries = Education.objects.filter(cv=profile)
        return Response(EducationSerializer(entries, many=True).data)
