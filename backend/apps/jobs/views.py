"""Read and manage the harvested jobs.

Everything here is written for a table that will hold millions of rows, so the
rules are: never return an unbounded list, never filter on something without an
index, and never make the database read rows it can discard.
"""

from functools import partial
from hashlib import md5

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.cache import cache
from django.core.paginator import Paginator as DjangoPaginator
from django.db.models import Count, F, Max, Min
from django.shortcuts import get_object_or_404
from django.utils.functional import cached_property

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import CVProfile
from apps.jobs.constants import COUNT_CACHE_SECONDS, JOB_STATS_CACHE_KEY, JOB_STATS_CACHE_SECONDS
from apps.jobs.models import Job, TrackedCompany
from apps.jobs.services.cv_ranking import (
    NotEnoughSkills,
    matched_skills_for,
    rank_by_cv,
)
from apps.jobs.serializers import (
    JobDetailSerializer,
    JobListSerializer,
    TrackedCompanySerializer,
)


# Columns the card renders. Everything else — the description above all — is
# left out of list queries.
_LIST_FIELDS = (
    'id', 'title', 'company_name', 'location_raw', 'remote_type',
    'employment_type', 'department', 'salary_text', 'source',
    'apply_url', 'posted_at', 'last_seen_at',
)


class _CachedCountPaginator(DjangoPaginator):
    """A paginator that does not re-count the same filtered set for every page.

    `COUNT(*)` over a filtered set is O(matches) and Postgres cannot answer it
    from an index — it recheck-scans the heap. Measured here: 78ms for a search
    matching 465 of 2,758 rows, and it is run *again* for page 2, page 3 and
    every keystroke that lands on the same filters.

    The count is cached against the filters that produced it, so paging is one
    cheap page query instead of a page query plus a full recount.
    """

    def __init__(self, *args, cache_key=None, **kwargs):
        self._cache_key = cache_key
        super().__init__(*args, **kwargs)

    @cached_property
    def count(self):
        if not self._cache_key:
            return super().count

        cached = cache.get(self._cache_key)
        if cached is None:
            cached = super().count
            cache.set(self._cache_key, cached, COUNT_CACHE_SECONDS)
        return cached


class JobPagination(PageNumberPagination):
    """Always paginated. An unbounded list is the one query guaranteed to break
    as the table grows, so there is no way to ask for everything."""

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        self.django_paginator_class = partial(
            _CachedCountPaginator, cache_key=_count_cache_key(request),
        )
        return super().paginate_queryset(queryset, request, view)


def _count_cache_key(request):
    """A key for the filter set, not the page.

    `page` and `page_size` are excluded on purpose — they select a window into
    a result set whose size they do not change, which is the whole point.
    `match=cv` ranks against the caller's own CV, so that key is per-user.
    """
    params = request.query_params
    filters = '|'.join(
        f'{name}={(params.get(name) or "").strip().casefold()}'
        for name in ('search', 'location', 'source', 'remote_type', 'company', 'match')
    )
    scope = request.user.pk if params.get('match') == 'cv' else 'all'
    return f'jobs:count:v1:{scope}:{md5(filters.encode()).hexdigest()}'


class JobListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Job.objects.all()

        # Full-text search against the stored vector, so Postgres uses the GIN
        # index. An `icontains` here would force a sequential scan of every row
        # and is the difference between milliseconds and minutes at scale.
        search = (request.query_params.get('search') or '').strip()
        if search:
            query = SearchQuery(search, config='english')
            queryset = (
                queryset.filter(search_vector=query)
                .annotate(rank=SearchRank(F('search_vector'), query))
                .order_by('-rank', '-posted_at')
            )

        # A substring match on the raw string, backed by the trigram index in
        # migration 0002. `location_city` / `location_country` are normalised
        # and indexed, but half of real listings resolve to neither — "Remote",
        # "Cardiff, London or Remote (UK)" — so filtering on them alone would
        # silently drop rows the user can see on the card.
        location = (request.query_params.get('location') or '').strip()
        if location:
            queryset = queryset.filter(location_raw__icontains=location)

        # These two map directly to composite indexes on the model.
        source = (request.query_params.get('source') or '').strip()
        if source:
            queryset = queryset.filter(source=source)

        remote = (request.query_params.get('remote_type') or '').strip()
        if remote:
            queryset = queryset.filter(remote_type=remote)

        company = (request.query_params.get('company') or '').strip()
        if company:
            queryset = queryset.filter(company_name__iexact=company)

        # Rank against the user's CV instead of by date. Deterministic skill
        # overlap, not an AI call — see services/cv_ranking.py.
        cv_terms = None
        if request.query_params.get('match') == 'cv':
            profile = CVProfile.objects.filter(user=request.user).first()
            if profile is None:
                return Response(
                    {'detail': 'Create your CV first — we match jobs against its skills.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                queryset, cv_terms = rank_by_cv(queryset, profile)
            except NotEnoughSkills as exc:
                return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # When ranking by CV we need the description to report which skills
        # matched, so it is loaded for the page only — never for the whole set.
        if cv_terms:
            queryset = queryset.only(*_LIST_FIELDS, 'description')
        else:
            queryset = queryset.only(*_LIST_FIELDS)

        paginator = JobPagination()
        page = paginator.paginate_queryset(queryset, request)
        data = JobListSerializer(page, many=True).data

        if cv_terms:
            # Computed over the 25 rows being returned, so it costs nothing.
            for item, job in zip(data, page):
                item['matched_skills'] = matched_skills_for(
                    f'{job.title} {job.description}', cv_terms,
                )

        response = paginator.get_paginated_response(data)
        if cv_terms:
            response.data['matched_against'] = cv_terms
        return response


class JobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(JobDetailSerializer(get_object_or_404(Job, pk=pk)).data)

    def delete(self, request, pk):
        """Remove a job from our copy.

        A hard delete is right here, unlike elsewhere in the app: this is
        harvested public data, not the user's own work, and the next nightly run
        will bring it back if the employer still lists it. Nothing is lost that
        cannot be re-fetched.
        """
        get_object_or_404(Job, pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobStatsView(APIView):
    """What is in the table, and how healthy the last gather was.

    **Cached, because none of this is cheap and none of it is fresh.** A total
    `COUNT(*)` and a grouped count both scan the whole table — fine at a few
    thousand rows, minutes at the millions this schema is built for — and the
    numbers only move when the nightly gather runs. The dashboard and the jobs
    header both request this on every load, so uncached it was the most
    expensive thing an idle user could do.

    The window is deliberately short: a just-finished gather should show up
    without waiting for a deploy, and a stale total is only ever cosmetic.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        payload = cache.get(JOB_STATS_CACHE_KEY)

        if payload is None:
            dates = Job.objects.aggregate(newest=Max('posted_at'), oldest=Min('posted_at'))
            payload = {
                'total_jobs': Job.objects.count(),
                'by_source': list(
                    Job.objects.values('source').annotate(count=Count('id')).order_by('-count')
                ),
                'newest_posted_at': dates['newest'],
                'oldest_posted_at': dates['oldest'],
            }
            cache.set(JOB_STATS_CACHE_KEY, payload, JOB_STATS_CACHE_SECONDS)

        # Company health is read live: it is 13 rows, and a board that broke
        # tonight is exactly the thing nobody should learn five minutes late.
        return Response({
            **payload,
            'companies': TrackedCompanySerializer(
                TrackedCompany.objects.all(), many=True,
            ).data,
        })
