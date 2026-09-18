"""Celery entry points for the job pipeline."""

import logging

from celery import shared_task

from apps.jobs.services.runner import run_gather

logger = logging.getLogger(__name__)


@shared_task
def gather_jobs():
    """The daily harvest. Registered in `setup_job_beat_tasks`.

    Returns the summary so it lands in the Celery result backend and a failed
    night can be inspected without trawling logs.
    """
    return run_gather()
