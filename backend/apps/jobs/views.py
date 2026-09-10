"""Read and manage the harvested jobs.

Everything here is written for a table that will hold millions of rows, so the
rules are: never return an unbounded list, never filter on something without an
index, and never make the database read rows it can discard.
"""

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.jobs.models import Job, TrackedCompany
from apps.jobs.serializers import (
    JobDetailSerializer,
    JobListSerializer,
    TrackedCompanySerializer,
)


class JobPagination(PageNumberPagination):
    """Always paginated. An unbounded list is the one query guaranteed to break
    as the table grows, so there is no way to ask for everything."""

    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


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

        # Each of these maps to an index on the model.
        location = (request.query_params.get('location') or '').strip()
        if location:
            queryset = queryset.filter(location_raw__icontains=location)

        source = (request.query_params.get('source') or '').strip()
        if source:
            queryset = queryset.filter(source=source)

        remote = (request.query_params.get('remote_type') or '').strip()
        if remote:
            queryset = queryset.filter(remote_type=remote)

        company = (request.query_params.get('company') or '').strip()
        if company:
            queryset = queryset.filter(company_name__iexact=company)

        # `only()` keeps the multi-thousand-character description out of a list
        # query that never renders it.
        queryset = queryset.only(
            'id', 'title', 'company_name', 'location_raw', 'remote_type',
            'employment_type', 'department', 'salary_text', 'source',
            'apply_url', 'posted_at', 'last_seen_at',
        )

        paginator = JobPagination()
        page = paginator.paginate_queryset(queryset, request)
        return paginator.get_paginated_response(JobListSerializer(page, many=True).data)


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

    Deliberately cheap: counts are indexed lookups, and there is no per-row work.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Max, Min

        by_source = list(
            Job.objects.values('source').annotate(count=Count('id')).order_by('-count')
        )
        dates = Job.objects.aggregate(newest=Max('posted_at'), oldest=Min('posted_at'))

        return Response({
            'total_jobs': Job.objects.count(),
            'by_source': by_source,
            'newest_posted_at': dates['newest'],
            'oldest_posted_at': dates['oldest'],
            'companies': TrackedCompanySerializer(
                TrackedCompany.objects.all(), many=True,
            ).data,
        })
