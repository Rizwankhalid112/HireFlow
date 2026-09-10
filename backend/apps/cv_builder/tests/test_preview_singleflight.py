"""Concurrent identical requests must cost exactly one render.

With only a handful of gunicorn workers this is not an optimisation. Three rapid
saves becoming three ~360ms WeasyPrint renders would starve the very save
requests the user is waiting on.

Note the transaction=True: Django's default test case wraps each test in a
transaction that other threads cannot see, so a threaded test against the normal
fixture either deadlocks or renders an empty CV — and then passes for the wrong
reason.
"""

import threading

import pytest
from django.core.cache import cache
from django.db import connection

from apps.cv_builder.services import pdf_renderer

THREADS = 4


@pytest.mark.django_db(transaction=True)
def test_concurrent_identical_requests_render_once(sample_cv):
    render_count = 0
    counter_lock = threading.Lock()
    original = pdf_renderer._render

    def counting_render(plan, cv):
        nonlocal render_count
        with counter_lock:
            render_count += 1
        return original(plan, cv)

    results = []
    start = threading.Barrier(THREADS)

    def worker():
        try:
            start.wait(timeout=10)
            results.append(pdf_renderer.render_cv_pdf(sample_cv, 'minimal'))
        finally:
            # Each thread opens its own connection; leaving them open blocks the
            # post-test truncation.
            connection.close()

    pdf_renderer._render = counting_render
    try:
        threads = [threading.Thread(target=worker) for _ in range(THREADS)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
    finally:
        pdf_renderer._render = original

    assert len(results) == THREADS, 'a worker failed'
    assert render_count == 1, f'{THREADS} concurrent requests caused {render_count} renders'

    # Every caller got the same document, not just the same page count.
    assert len({pdf for pdf, _ in results}) == 1


@pytest.mark.django_db
def test_a_stale_lock_does_not_hang_the_request(sample_cv, monkeypatch):
    """If the lock holder dies mid-render nobody will ever fill the cache, so
    the waiter renders anyway rather than blocking for the full lock TTL."""
    monkeypatch.setattr(pdf_renderer, 'LOCK_WAIT_SECONDS', 0.2)

    plan = pdf_renderer.build_render_plan(sample_cv, 'minimal')
    # A worker that acquired the lock and was then killed: the lock is held but
    # the cache entry it promised never arrives.
    cache.add(f'{plan.cache_key}:lock', 1, pdf_renderer.LOCK_TTL)

    pdf_bytes, page_count = pdf_renderer.render_cv_pdf(sample_cv, 'minimal')

    assert pdf_bytes.startswith(b'%PDF')
    assert page_count >= 1
