"""Run the gather by hand — for a first load, a new company, or debugging."""

from django.core.management.base import BaseCommand

from apps.jobs.models import TrackedCompany
from apps.jobs.services.runner import run_gather


class Command(BaseCommand):
    help = 'Fetch jobs from every active tracked company into the jobs table.'

    def add_arguments(self, parser):
        parser.add_argument('--platform', help='Only this platform (greenhouse, ashby, lever, workable).')
        parser.add_argument('--slug', help='Only this company slug.')
        parser.add_argument('--no-purge', action='store_true', help='Skip the retention sweep.')
        parser.add_argument('--workers', type=int, default=4)

    def handle(self, *args, **options):
        companies = TrackedCompany.objects.filter(is_active=True)
        if options.get('platform'):
            companies = companies.filter(platform=options['platform'])
        if options.get('slug'):
            companies = companies.filter(slug=options['slug'])

        if not companies.exists():
            self.stdout.write(self.style.WARNING('No matching active companies. Run seed_companies first.'))
            return

        self.stdout.write(f'Fetching {companies.count()} companies…')
        summary = run_gather(
            companies=companies,
            purge_days=0 if options['no_purge'] else None,
            workers=options['workers'],
        )

        style = self.style.SUCCESS if not summary['failed'] else self.style.WARNING
        self.stdout.write(style(
            f"{summary['succeeded']}/{summary['companies']} companies ok · "
            f"{summary['jobs_written']} jobs written · "
            f"{summary['purged']} purged · {summary['seconds']}s"
        ))
        for name, error in summary['errors']:
            self.stdout.write(self.style.ERROR(f'  {name}: {error}'))
