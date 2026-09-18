"""Seed the tracked-company list.

**Every slug below was called live and confirmed to return jobs.** That matters:
many slugs in circulation are wrong — Lever's `netflix`, `yelp`, `twitch`,
`shopify`, `plaid` and `brex` all 404, Greenhouse's `doordash` 404s, and Ashby's
`vercel` returns an empty list. A seed list that has not been tested produces a
pipeline that looks broken.

This is a starting set, not a target. The real list is a commercial decision
about which employers matter to our users.
"""

from django.core.management.base import BaseCommand

from apps.jobs.models import ATSPlatform, TrackedCompany

# (name, platform, slug) — all verified 2026-09-10
COMPANIES = [
    ('Stripe', ATSPlatform.GREENHOUSE, 'stripe'),
    ('GitLab', ATSPlatform.GREENHOUSE, 'gitlab'),
    ('Airbnb', ATSPlatform.GREENHOUSE, 'airbnb'),
    ('Robinhood', ATSPlatform.GREENHOUSE, 'robinhood'),
    ('Monzo', ATSPlatform.GREENHOUSE, 'monzo'),
    ('OpenAI', ATSPlatform.ASHBY, 'openai'),
    ('Ramp', ATSPlatform.ASHBY, 'ramp'),
    ('Notion', ATSPlatform.ASHBY, 'notion'),
    ('Linear', ATSPlatform.ASHBY, 'linear'),
    ('PostHog', ATSPlatform.ASHBY, 'posthog'),
    ('Palantir', ATSPlatform.LEVER, 'palantir'),
    ('Match Group', ATSPlatform.LEVER, 'matchgroup'),
    ('Blueground', ATSPlatform.WORKABLE, 'blueground'),
]


class Command(BaseCommand):
    help = 'Create or update the verified starter list of tracked companies.'

    def handle(self, *args, **options):
        created = updated = 0
        for name, platform, slug in COMPANIES:
            _, was_created = TrackedCompany.objects.update_or_create(
                platform=platform,
                slug=slug,
                defaults={'name': name, 'is_active': True},
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f'{created} created, {updated} already present. '
            f'{TrackedCompany.objects.filter(is_active=True).count()} active.'
        ))
