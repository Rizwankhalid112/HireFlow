"""Write fetched jobs into the table, quickly and idempotently.

This is the part that has to stay fast as the table grows, so three decisions
matter more than the rest:

- **Bulk, not row-by-row.** A 616-job board written one INSERT at a time is 616
  round trips and 616 index updates inside a transaction other requests are
  waiting on. `bulk_create` with `update_conflicts` does it in one statement.
- **Upsert on `(source, external_id)`.** Re-running the fetch updates rows
  instead of inserting them, so a nightly run does not double the table.
- **`search_vector` is written on ingest, not computed per query.** Building it
  at read time would mean a sequential scan; storing it lets the GIN index do
  the work. It is refreshed only for the rows we just touched.

Everything here is per-company so one bad board cannot take down a run.
"""

import logging

from django.contrib.postgres.search import SearchVector
from django.db import transaction
from django.utils import timezone

from apps.jobs.models import Job

logger = logging.getLogger(__name__)

# Rows per statement. Large enough that the round trips disappear, small enough
# that one statement does not hold a lock for long or balloon memory.
BATCH_SIZE = 500

# Columns a re-fetch is allowed to overwrite. `first_seen_at` is deliberately
# absent — it records when we first saw the job and must survive every later run.
UPDATE_FIELDS = [
    'company', 'company_name', 'title', 'description', 'apply_url',
    'location_raw', 'location_city', 'location_country', 'remote_type',
    'employment_type', 'department', 'salary_text', 'posted_at',
    'last_seen_at', 'updated_at',
]


def upsert_jobs(rows, company=None):
    """Insert or update `rows`. Returns `(written, skipped)`.

    `last_seen_at` is stamped on every row in this run — that is what retention
    later reads, and it is the reason a job that quietly disappears from an
    employer's feed can be told apart from one that is still open.
    """
    now = timezone.now()
    objects, seen, skipped = [], set(), 0

    for row in rows:
        key = (row['source'], row['external_id'])
        # A feed occasionally repeats an id within one response; the unique
        # constraint would reject the whole batch, so it is caught here.
        if not row['external_id'] or not row['title'] or not row['apply_url'] or key in seen:
            skipped += 1
            continue
        seen.add(key)
        objects.append(Job(
            company=company,
            last_seen_at=now,
            first_seen_at=now,
            **row,
        ))

    if not objects:
        return 0, skipped

    with transaction.atomic():
        Job.objects.bulk_create(
            objects,
            batch_size=BATCH_SIZE,
            update_conflicts=True,
            update_fields=UPDATE_FIELDS,
            unique_fields=['source', 'external_id'],
        )
        _refresh_search_vectors([(o.source, o.external_id) for o in objects])

    return len(objects), skipped


def _refresh_search_vectors(keys):
    """Rebuild the stored search vector for just-written rows.

    Scoped to this batch rather than the whole table: recomputing every row
    nightly would be the single most expensive thing the pipeline does, and
    nothing about untouched rows has changed.

    Weighted A-D so ranking is sensible: a job whose *title* says Python beats
    one that merely mentions it in the body, and searching "stripe" ranks a job
    titled for Stripe above the hundreds merely posted by Stripe.

    The description is included despite being by far the largest field, because
    excluding it makes the feature wrong: searching "python" over 2,700 real
    engineering jobs matched **one**, since most listings name the language in
    the body rather than the title. It costs index size — the honest trade — but
    a fast search that cannot find things is not worth having.
    """
    if not keys:
        return
    # Scoped by source as well as id: two platforms can issue the same
    # external_id, and filtering on the id alone would rewrite another source's
    # rows. Every batch comes from one source, so one value is enough.
    source = keys[0][0]
    externals = [k[1] for k in keys]
    for start in range(0, len(externals), BATCH_SIZE):
        chunk = externals[start:start + BATCH_SIZE]
        Job.objects.filter(source=source, external_id__in=chunk).update(
            search_vector=(
                SearchVector('title', weight='A', config='english')
                + SearchVector('company_name', weight='B', config='english')
                + SearchVector('location_raw', weight='C', config='english')
                + SearchVector('description', weight='D', config='english')
            )
        )


def purge_stale(days):
    """Delete jobs we have not seen in the feed for `days`.

    **Keyed on `last_seen_at`, never on `posted_at`.** Employers keep evergreen
    requisitions open for years — one tested board publishes a live role as
    posted in 2009 — so deleting by posting age would remove jobs that are
    genuinely open. Disappearing from the feed is the only reliable signal that
    a listing has closed.
    """
    # A retention window of zero or less would mean "delete everything older
    # than right now", i.e. the whole table. That is never what a caller wants,
    # so it is read as "do not purge" — the safe reading of an ambiguous value.
    if not days or days <= 0:
        return 0

    cutoff = timezone.now() - timezone.timedelta(days=days)
    deleted, _ = Job.objects.filter(last_seen_at__lt=cutoff).delete()
    if deleted:
        logger.info('Purged %d job(s) unseen since %s', deleted, cutoff.date())
    return deleted
