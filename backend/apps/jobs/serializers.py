from rest_framework import serializers

from apps.jobs.models import Job, TrackedCompany


class JobListSerializer(serializers.ModelSerializer):
    """The card. Deliberately excludes `description`, which is several thousand
    characters — sending 50 of those per page would dominate the response."""

    age_days = serializers.IntegerField(read_only=True)
    is_long_running = serializers.BooleanField(read_only=True)
    source_label = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = Job
        fields = (
            'id', 'title', 'company_name', 'location_raw', 'remote_type',
            'employment_type', 'department', 'salary_text',
            'source', 'source_label', 'apply_url',
            'posted_at', 'age_days', 'is_long_running', 'last_seen_at',
        )


class JobDetailSerializer(JobListSerializer):
    class Meta(JobListSerializer.Meta):
        fields = JobListSerializer.Meta.fields + ('description', 'first_seen_at')


class TrackedCompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackedCompany
        fields = (
            'id', 'name', 'platform', 'slug', 'is_active',
            'last_fetched_at', 'last_fetch_status', 'last_job_count',
        )
