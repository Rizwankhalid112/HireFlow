from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import CVCertification, CVLanguage, CVProject
from apps.cv_builder.serializers.project import (
    CVCertificationSerializer,
    CVLanguageSerializer,
    CVProjectSerializer,
)
from apps.cv_builder.utils import get_user_cv_profile, reorder_owned_items


class _ReorderMixin:
    model = None
    serializer_class = None

    def patch_reorder(self, request):
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ValidationError({'ordered_ids': 'A non-empty list of IDs is required.'})

        try:
            reorder_owned_items(self.model, ordered_ids, {'cv__user': request.user})
        except ValueError as exc:
            raise ValidationError({'ordered_ids': str(exc)}) from exc

        profile = get_user_cv_profile(request.user)
        items = self.model.objects.filter(cv=profile)
        return Response(self.serializer_class(items, many=True).data)


class ProjectListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        projects = CVProject.objects.filter(cv=profile)
        return Response(CVProjectSerializer(projects, many=True).data)

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(cv=profile)
        return Response(CVProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return CVProject.objects.get(id=pk, cv__user=request.user)
        except CVProject.DoesNotExist:
            raise NotFound('Project not found.')

    def put(self, request, pk):
        project = self.get_object(request, pk)
        serializer = CVProjectSerializer(project, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CVProjectSerializer(project).data)

    def delete(self, request, pk):
        project = self.get_object(request, pk)
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectReorderView(_ReorderMixin, APIView):
    permission_classes = [IsAuthenticated]
    model = CVProject
    serializer_class = CVProjectSerializer

    def patch(self, request):
        return self.patch_reorder(request)


class CertificationListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        certs = CVCertification.objects.filter(cv=profile)
        return Response(CVCertificationSerializer(certs, many=True).data)

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVCertificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cert = serializer.save(cv=profile)
        return Response(CVCertificationSerializer(cert).data, status=status.HTTP_201_CREATED)


class CertificationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return CVCertification.objects.get(id=pk, cv__user=request.user)
        except CVCertification.DoesNotExist:
            raise NotFound('Certification not found.')

    def put(self, request, pk):
        cert = self.get_object(request, pk)
        serializer = CVCertificationSerializer(cert, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CVCertificationSerializer(cert).data)

    def delete(self, request, pk):
        cert = self.get_object(request, pk)
        cert.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CertificationReorderView(_ReorderMixin, APIView):
    permission_classes = [IsAuthenticated]
    model = CVCertification
    serializer_class = CVCertificationSerializer

    def patch(self, request):
        return self.patch_reorder(request)


class LanguageListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        languages = CVLanguage.objects.filter(cv=profile)
        return Response(CVLanguageSerializer(languages, many=True).data)

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVLanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        language = serializer.save(cv=profile)
        return Response(CVLanguageSerializer(language).data, status=status.HTTP_201_CREATED)


class LanguageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return CVLanguage.objects.get(id=pk, cv__user=request.user)
        except CVLanguage.DoesNotExist:
            raise NotFound('Language not found.')

    def put(self, request, pk):
        language = self.get_object(request, pk)
        serializer = CVLanguageSerializer(language, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CVLanguageSerializer(language).data)

    def delete(self, request, pk):
        language = self.get_object(request, pk)
        language.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LanguageReorderView(_ReorderMixin, APIView):
    permission_classes = [IsAuthenticated]
    model = CVLanguage
    serializer_class = CVLanguageSerializer

    def patch(self, request):
        return self.patch_reorder(request)
