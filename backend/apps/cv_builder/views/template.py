from django.http import HttpResponse

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.serializers.photo import CVPhotoSerializer
from apps.cv_builder.services.pdf_renderer import RenderError, render_cv_meta, render_cv_pdf
from apps.cv_builder.templates_registry import get_template, public_registry
from apps.cv_builder.utils import get_user_cv_profile


def _requested_template(request):
    """Validate ?template= against the registry allowlist.

    Never trust this value into a path — get_template() is a dict lookup.
    """
    template_id = request.query_params.get('template')
    if not template_id:
        return None
    if not get_template(template_id):
        raise ValidationError({'template': 'Unknown template.'})
    return template_id


class TemplateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(public_registry())


class CVPreviewView(APIView):
    """The rendered PDF, inline.

    Byte-identical to the export download — same render, same cache entry, only
    the Content-Disposition differs. That is what makes the on-screen preview an
    exact snapshot of the file the user gets.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        template_id = _requested_template(request)

        try:
            pdf_bytes, _ = render_cv_pdf(profile, template_id)
        except RenderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="cv-preview.pdf"'
        return response


class CVPreviewMetaView(APIView):
    """Page count and overflow flag, measured from the laid-out document."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        template_id = _requested_template(request)

        try:
            return Response(render_cv_meta(profile, template_id))
        except RenderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class CVPhotoView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVPhotoSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'photo': profile.photo.url if profile.photo else None})

    def delete(self, request):
        profile = get_user_cv_profile(request.user)
        if profile.photo:
            profile.photo.delete(save=False)
            profile.photo = None
            profile.save(update_fields=['photo'])
        return Response(status=status.HTTP_204_NO_CONTENT)
