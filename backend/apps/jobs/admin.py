from django.contrib import admin

from apps.jobs.models import Job, TrackedCompany


@admin.register(TrackedCompany)
class TrackedCompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'platform', 'slug', 'is_active', 'last_job_count', 'last_fetched_at', 'last_fetch_status')
    list_filter = ('platform', 'is_active')
    search_fields = ('name', 'slug')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('title', 'company_name', 'source', 'location_raw', 'posted_at', 'last_seen_at')
    list_filter = ('source', 'remote_type')
    search_fields = ('title', 'company_name')
    # The table is large; a count(*) for the paginator would be the slowest
    # query on the page.
    show_full_result_count = False
    date_hierarchy = 'posted_at'
