"""Views owned by the project rather than by an app."""

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse


def health_check(request):
    """Liveness probe. Used by the compose healthcheck and by the host."""
    return JsonResponse({'status': 'ok'})


def spa(request):
    """Serve the React shell for any path the API does not own.

    The routes that matter here are the ones we *email* people —
    `/verify-email/<token>` and `/reset-password/<token>`. They exist only in
    the client-side router, so without this the server 404s them and nobody can
    finish registering or recover an account.

    `no-store` is deliberate. index.html names the hashed asset bundles, so a
    cached copy survives a deploy and asks the browser for filenames that are
    no longer there — a blank page that a refresh does not fix. The assets
    themselves are immutable and cached hard by WhiteNoise.
    """
    index = Path(settings.FRONTEND_DIST) / 'index.html'

    if not index.is_file():
        raise Http404('No frontend build in this image.')

    response = FileResponse(index.open('rb'), content_type='text/html')
    response['Cache-Control'] = 'no-store, must-revalidate'
    return response
