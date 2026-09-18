from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.cv_builder.models import SkillCanonical


class Command(BaseCommand):
    help = 'Load canonical skills from the cv_builder fixture'

    def handle(self, *args, **options):
        call_command('loaddata', 'canonical_skills', app_label='cv_builder')
        count = SkillCanonical.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Canonical skills seeded. Total: {count}'))
