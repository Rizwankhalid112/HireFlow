from django.urls import path

from apps.jobs.views import JobDetailView, JobListView, JobStatsView

urlpatterns = [
    path('', JobListView.as_view(), name='job-list'),
    path('stats/', JobStatsView.as_view(), name='job-stats'),
    path('<uuid:pk>/', JobDetailView.as_view(), name='job-detail'),
]
