from django.core.management.base import BaseCommand

from apps.cv_builder.services.thumbnails import ThumbnailError, render_template_thumbnail
from apps.cv_builder.templates_registry import CV_TEMPLATES


class Command(BaseCommand):
    help = (
        'Pre-render the template gallery thumbnails into the cache. '
        'Run after deploying, or after changing a CV template, so the first '
        'visitor does not pay the ~500ms-per-template cold render.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-render even if a cached thumbnail already exists.',
        )

    def handle(self, *args, **options):
        force = options['force']
        failures = 0

        for template_id in CV_TEMPLATES:
            try:
                png = render_template_thumbnail(template_id, use_cache=not force)
            except ThumbnailError as exc:
                failures += 1
                self.stderr.write(self.style.ERROR(f'{template_id}: {exc}'))
                continue

            self.stdout.write(f'{template_id}: {len(png) // 1024} KB cached')

        if failures:
            self.stderr.write(self.style.WARNING(f'{failures} template(s) failed'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{len(CV_TEMPLATES)} thumbnails ready'))
