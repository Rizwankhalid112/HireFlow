from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from apps.accounts.urls import auth_urlpatterns, user_urlpatterns
from config.views import health_check, spa

urlpatterns = [
    path('health/', health_check, name='health'),
    path('admin/', admin.site.urls),
    path('api/auth/', include(auth_urlpatterns)),
    path('api/users/', include(user_urlpatterns)),
    path('api/cv/', include('apps.cv_builder.urls')),
    path('api/jobs/', include('apps.jobs.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Single-service deploys bundle the React build into this image; Compose does
# not, and the pattern is simply never registered there.
#
# The negative lookahead is the whole safety of this route. Registered last it
# would still shadow nothing, but an unanchored catch-all is one refactor away
# from swallowing /api/ and turning every API 404 into an HTML page — which
# fails as a confusing JSON parse error in the client rather than as a 404.
if settings.SERVE_SPA:
    urlpatterns += [
        re_path(r'^(?!api/|admin/|static/|media/|health/).*$', spa, name='spa'),
    ]
