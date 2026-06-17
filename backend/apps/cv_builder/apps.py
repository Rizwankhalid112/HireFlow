from django.apps import AppConfig


class CvBuilderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.cv_builder'
    label = 'cv_builder'

    def ready(self):
        import apps.cv_builder.signals  # noqa: F401
