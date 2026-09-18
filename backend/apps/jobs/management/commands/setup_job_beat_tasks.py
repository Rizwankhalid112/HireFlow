"""Register the nightly gather with Celery Beat."""

from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Register the daily job-gather periodic task.'

    def handle(self, *args, **options):
        # 03:00 UTC: outside working hours in our main markets, and far from the
        # CV Builder's own retention jobs so the two never contend.
        schedule, _ = CrontabSchedule.objects.get_or_create(
            minute='0', hour='3', day_of_week='*', day_of_month='*',
            month_of_year='*', timezone='UTC',
        )
        PeriodicTask.objects.update_or_create(
            name='jobs_gather_daily',
            defaults={'task': 'apps.jobs.tasks.gather_jobs', 'crontab': schedule, 'enabled': True},
        )
        self.stdout.write(self.style.SUCCESS('Registered jobs_gather_daily (03:00 UTC).'))
