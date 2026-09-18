"""Job listings gathered from public ATS feeds.

Two tables. `TrackedCompany` is the input — the list of employers we poll.
`Job` is everything we have harvested from them.

The shape of `Job` is driven by what the source data actually looks like, which
was measured before this was written (see JOB_SOURCES_RND.md). Three findings in
particular are baked into the schema rather than handled later:

- **Retention keys on `last_seen_at`, not on `posted_at`.** Live Palantir
  listings carry a published date of 2009. Deleting on posting age would remove
  jobs that are genuinely open; deleting on "we stopped seeing it in the feed"
  removes exactly the ones that closed.
- **`posted_at` can be older than reality, never newer.** Greenhouse's
  `first_published` is correct for most jobs and too old for reposted
  requisitions. The error is one-directional, which is safe — we under-sell
  freshness rather than presenting a stale job as new.
- **The source matters to the reader.** Which board a job came from is part of
  the record, not plumbing, so it is a first-class indexed column and is shown
  in the UI.
"""

import uuid

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models
from django.utils import timezone


class ATSPlatform(models.TextChoices):
    """Only platforms we have tested and are permitted to use.

    SmartRecruiters and Recruitee are deliberately absent: both were tested and
    return nothing usable. LinkedIn, Indeed and Glassdoor are absent because
    their terms prohibit it — see JOB_SOURCES_RND.md §6.
    """

    GREENHOUSE = 'greenhouse', 'Greenhouse'
    ASHBY = 'ashby', 'Ashby'
    LEVER = 'lever', 'Lever'
    WORKABLE = 'workable', 'Workable'


class RemoteType(models.TextChoices):
    REMOTE = 'remote', 'Remote'
    HYBRID = 'hybrid', 'Hybrid'
    ONSITE = 'onsite', 'On-site'
    UNKNOWN = '', 'Not stated'


class TrackedCompany(models.Model):
    """One employer whose board we poll daily.

    `slug` is the identifier in that platform's URL, and it is not guessable —
    several widely-circulated slugs turned out to be wrong when tested. Hence
    `last_fetch_status`: a company that silently stopped returning jobs should be
    visible, not just absent from the results.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    platform = models.CharField(max_length=20, choices=ATSPlatform.choices)
    slug = models.CharField(max_length=120, help_text="Identifier in the ATS URL.")
    is_active = models.BooleanField(default=True)

    last_fetched_at = models.DateTimeField(null=True, blank=True)
    last_fetch_status = models.CharField(max_length=200, blank=True, default='')
    last_job_count = models.IntegerField(default=0)
    consecutive_failures = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'jobs_tracked_company'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['platform', 'slug'], name='uniq_company_platform_slug',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.platform})'


class Job(models.Model):
    """One job listing.

    At a few million rows the only thing that keeps this table usable is that no
    common query has to read all of it — see the indexes below, each of which
    exists for a specific query the API actually makes.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # --- provenance: which board, and its id there ---------------------------
    source = models.CharField(max_length=20, choices=ATSPlatform.choices, db_index=True)
    external_id = models.CharField(max_length=120)
    company = models.ForeignKey(
        TrackedCompany, on_delete=models.CASCADE, related_name='jobs', null=True, blank=True,
    )
    company_name = models.CharField(max_length=200, db_index=True)

    # --- the listing ---------------------------------------------------------
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default='')
    apply_url = models.URLField(max_length=600)

    location_raw = models.CharField(
        max_length=300, blank=True, default='',
        help_text='Exactly as the source wrote it. Never overwritten.',
    )
    # Normalised for filtering. Approximate by nature — every platform writes
    # location differently and some write "N/A" — so the raw value is kept
    # alongside and is what we display.
    location_city = models.CharField(max_length=120, blank=True, default='', db_index=True)
    location_country = models.CharField(max_length=120, blank=True, default='', db_index=True)
    remote_type = models.CharField(
        max_length=10, choices=RemoteType.choices, blank=True, default='', db_index=True,
    )

    employment_type = models.CharField(max_length=40, blank=True, default='')
    department = models.CharField(max_length=200, blank=True, default='')
    # Display only, never a filter: presence is a per-company opt-in and ranges
    # from 0% to 97% of jobs within a single platform.
    salary_text = models.CharField(max_length=200, blank=True, default='')

    # --- dates ---------------------------------------------------------------
    posted_at = models.DateTimeField(
        null=True, blank=True, db_index=True,
        help_text='As published by the source. May be older than reality, never newer.',
    )
    # What retention runs on. Updated on every run in which the job is still
    # present in the feed, so it means "the employer still lists this".
    last_seen_at = models.DateTimeField(default=timezone.now, db_index=True)
    first_seen_at = models.DateTimeField(default=timezone.now)

    search_vector = SearchVectorField(null=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'jobs_job'
        ordering = ['-posted_at', '-last_seen_at']
        constraints = [
            # The de-duplication rule. Re-running the fetch updates rows rather
            # than inserting them, so the table does not double every night.
            models.UniqueConstraint(
                fields=['source', 'external_id'], name='uniq_job_source_external_id',
            ),
        ]
        indexes = [
            # Full-text search. A GIN index on a stored vector is what keeps
            # `search` fast at millions of rows — an `ILIKE '%term%'` cannot use
            # an index at all and degrades linearly.
            #
            # Measured on 2,713 real rows: forced through this index a search
            # runs in 0.19ms against 10.98ms for a sequential scan. Postgres
            # still chooses the seq scan at that size because the estimated
            # costs are nearly tied (430 vs 437) — correct of it, and it
            # switches to the index as the table grows. Do not "fix" a seq scan
            # seen on a small dev dataset.
            GinIndex(fields=['search_vector'], name='job_search_vector_gin'),
            # Substring search on the raw location. A leading wildcard cannot
            # use a btree, so without trigrams `?location=london` is the one
            # filter on this table guaranteed to sequential-scan.
            GinIndex(
                fields=['location_raw'],
                opclasses=['gin_trgm_ops'],
                name='job_location_trgm_idx',
            ),
            # The default listing: newest first.
            models.Index(fields=['-posted_at'], name='job_posted_desc_idx'),
            # Filter by location or remote type, then order by date. Composite
            # because filtering and ordering separately still means sorting a
            # large intermediate result.
            models.Index(fields=['location_country', '-posted_at'], name='job_country_posted_idx'),
            models.Index(fields=['remote_type', '-posted_at'], name='job_remote_posted_idx'),
            models.Index(fields=['source', '-posted_at'], name='job_source_posted_idx'),
            # Retention sweeps and per-company refreshes.
            models.Index(fields=['last_seen_at'], name='job_last_seen_idx'),
            models.Index(fields=['company', '-posted_at'], name='job_company_posted_idx'),
        ]

    def __str__(self):
        return f'{self.title} — {self.company_name}'

    @property
    def age_days(self):
        if not self.posted_at:
            return None
        return (timezone.now() - self.posted_at).days

    @property
    def is_long_running(self):
        """Open so long that showing an exact age would be noise.

        Some employers keep evergreen requisitions open for years — one tested
        listing is published as posted in 2009. The UI shows "long-running
        listing" rather than a five-figure day count.
        """
        age = self.age_days
        return age is not None and age > LONG_RUNNING_DAYS


# A year. Past this the exact number stops being information and starts being a
# distraction, and the listing is better described than counted.
LONG_RUNNING_DAYS = 365
