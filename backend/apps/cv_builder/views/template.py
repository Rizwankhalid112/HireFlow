from django.http import HttpResponse
from django.utils.http import parse_etags, quote_etag

from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.serializers.photo import CVPhotoSerializer
from apps.cv_builder.services.pdf_renderer import (
    RenderError,
    build_render_plan,
    render_cv_meta,
    render_from_plan,
)
from apps.cv_builder.services.thumbnails import ThumbnailError, render_template_thumbnail
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


def _client_has(request, etag):
    """True when the client's If-None-Match already covers `etag`.

    Handles the comma-separated list and the weak `W/` prefix, so a proxy that
    weakens the validator does not defeat the 304 path.
    """
    header = request.headers.get('If-None-Match')
    if not header:
        return False

    try:
        candidates = parse_etags(header)
    except ValueError:
        return False

    if '*' in candidates:
        return True

    def strong(value):
        return value[2:] if value.startswith('W/') else value

    return strong(etag) in {strong(candidate) for candidate in candidates}


class TemplateListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(public_registry())


class TemplateSampleView(APIView):
    """PNG of one template rendered with the demo CV, for the gallery.

    AllowAny on purpose: an <img src> cannot carry a Bearer token, and this
    contains no user data — it is the fixed sample CV, effectively a static
    asset. Never render real profile data through this endpoint.
    """

    permission_classes = [AllowAny]

    def get(self, request, template_id):
        try:
            png = render_template_thumbnail(template_id)
        except ThumbnailError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_404_NOT_FOUND)

        response = HttpResponse(png, content_type='image/png')
        # Safe to cache hard: the sample data is a constant.
        response['Cache-Control'] = 'public, max-age=86400'
        return response


def _validated_pdf(response, etag):
    """Attach the revalidation headers.

    `private` is not optional here — this is one user's CV, and a shared proxy
    caching it would hand it to somebody else.
    """
    response['ETag'] = etag
    response['Cache-Control'] = 'private, must-revalidate'
    return response


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

        # The plan is built without rendering, so an unchanged CV is answered
        # from the digest alone — the live preview re-requests on every save and
        # most of those requests are for content the client already holds.
        plan = build_render_plan(profile, template_id)
        etag = quote_etag(plan.digest)

        if _client_has(request, etag):
            return _validated_pdf(HttpResponse(status=status.HTTP_304_NOT_MODIFIED), etag)

        try:
            result = render_from_plan(profile, plan)
        except RenderError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        response = HttpResponse(result['pdf'], content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="cv-preview.pdf"'
        response['X-CV-Page-Count'] = str(result['page_count'])
        return _validated_pdf(response, etag)


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
