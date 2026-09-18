from django.core.management.base import BaseCommand
from django_celery_beat.models import CrontabSchedule, PeriodicTask


class Command(BaseCommand):
    help = 'Register CV Builder Celery Beat periodic tasks'

    def handle(self, *args, **options):
        tasks = [
            {
                'name': 'cv_builder_send_draft_reminder',
                'task': 'apps.cv_builder.tasks.send_draft_reminder',
                'crontab': {'hour': '9', 'minute': '0'},
            },
            {
                'name': 'cv_builder_delete_stale_drafts',
                'task': 'apps.cv_builder.tasks.delete_stale_drafts',
                'crontab': {'hour': '2', 'minute': '0'},
            },
            {
                'name': 'cv_builder_delete_orphaned_files',
                'task': 'apps.cv_builder.tasks.delete_orphaned_files',
                'crontab': {'hour': '3', 'minute': '0', 'day_of_week': '0'},
            },
            {
                # Every 5 minutes, not daily: this is what stops the frontend
                # polling a row whose worker died, so the delay before it fires
                # is time the user spends watching a spinner.
                'name': 'cv_builder_fail_stuck_uploads',
                'task': 'apps.cv_builder.tasks.fail_stuck_uploads',
                'crontab': {'hour': '*', 'minute': '*/5'},
            },
        ]

        for entry in tasks:
            schedule, _ = CrontabSchedule.objects.get_or_create(
                minute=entry['crontab']['minute'],
                hour=entry['crontab']['hour'],
                day_of_week=entry['crontab'].get('day_of_week', '*'),
                day_of_month='*',
                month_of_year='*',
                timezone='UTC',
            )
            PeriodicTask.objects.update_or_create(
                name=entry['name'],
                defaults={
                    'task': entry['task'],
                    'crontab': schedule,
                    'enabled': True,
                },
            )
            self.stdout.write(self.style.SUCCESS(f"Registered {entry['name']}"))
