"""A CV frozen against one job.

This is the model `job_match_rnd.md` §6 said could not be deferred a third time.
The tension it resolves: the product needs **a different CV per job**, while
`CVProfile` is one row per user and mutable. Tailoring by editing the profile
would corrupt the master CV and every previously tailored version at once.

So the master stays the single source of truth and is never written to here. A
tailored CV is a snapshot: the document as it was sent, the job it was sent for,
and the exact list of words that were changed to make it.

The document lives in the database rather than on disk because the host's
filesystem is wiped on every deploy — a storage room that loses documents fails
at precisely the moment it is wanted, which is months later.
"""

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from .cv_profile import CVProfile
from .job_match import JobMatch


def default_expiry():
    return timezone.now() + timedelta(days=settings.TAILORED_CV_RETENTION_DAYS)


class CVVersionQuerySet(models.QuerySet):
    def live(self):
        """Not yet expired. Every read path uses this.

        Expiry is enforced on read as well as by the purge command: the command
        can be late, or not run at all on a host without a scheduler, and a user
        should never open a CV the retention policy says is gone.
        """
        return self.filter(expires_at__gt=timezone.now())


class CVVersion(models.Model):
    class SourceType(models.TextChoices):
        PROFILE = 'profile', 'HireFlow CV'
        UPLOAD = 'upload', 'Uploaded file'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name='versions')

    # SET_NULL rather than CASCADE: deleting the analysis must not destroy the
    # document that came out of it. Everything the storage room lists is
    # denormalised below for exactly this reason.
    job_match = models.ForeignKey(
        JobMatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cv_versions',
    )

    # Denormalised so the storage room lists without a join, and survives the
    # match being deleted. This is what the user recognises months later.
    company = models.CharField(max_length=200, blank=True, default='')
    job_title = models.CharField(max_length=200, blank=True, default='')
    match_score = models.IntegerField(default=0)

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.PROFILE,
    )

    # For a CV built here: the frozen content and the template the user had
    # chosen at the time. Both are needed — re-rendering later against a
    # template they have since changed would not be the document they sent.
    content_json = models.JSONField(null=True, blank=True)
    template_id = models.CharField(max_length=50, blank=True, default='')

    # The tailored document itself.
    file_blob = models.BinaryField(null=True, blank=True, editable=False)
    file_name = models.CharField(max_length=300, blank=True, default='')
    file_mime = models.CharField(max_length=100, blank=True, default='')

    # Exactly which words were changed, and what they were before. This is the
    # change list the user reviews before accepting, kept afterwards so the
    # document can always be explained — the whole risk of this feature is
    # putting a word on a CV the user cannot account for in an interview.
    applied_rewrites = models.JSONField(default=list, blank=True)
    # Rewrites we refused to make, with the reason. Shown, never hidden: a
    # silent skip looks identical to a bug from the user's side.
    skipped_rewrites = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField(default=default_expiry, db_index=True)

    objects = CVVersionQuerySet.as_manager()

    class Meta:
        db_table = 'cv_versions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cv', '-created_at'], name='cv_version_recent_idx'),
        ]

    def __str__(self):
        label = self.company or self.job_title or 'Untitled'
        return f'{label} — {self.created_at:%d %b %Y}'

    @property
    def change_count(self):
        return len(self.applied_rewrites or [])
