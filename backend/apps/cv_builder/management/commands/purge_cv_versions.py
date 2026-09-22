"""Delete tailored CVs past their retention date.

These rows hold the documents themselves, so unbounded retention is unbounded
database growth. The read paths already filter on `expires_at`, so this command
reclaims space rather than enforcing the policy — if it never runs, users still
cannot see expired CVs.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.cv_builder.models import CVVersion


class Command(BaseCommand):
    help = 'Delete tailored CVs whose retention period has passed.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would be deleted without deleting it.',
        )

    def handle(self, *args, **options):
        expired = CVVersion.objects.filter(expires_at__lte=timezone.now())
        count = expired.count()

        if options['dry_run']:
            self.stdout.write(f'{count} tailored CV(s) would be deleted.')
            return

        expired.delete()
        self.stdout.write(self.style.SUCCESS(f'Deleted {count} expired tailored CV(s).'))
