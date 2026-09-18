import uuid

from django.db import models

from apps.cv_builder.models.cv_profile import CVProfile


class CVProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='projects',
    )
    name = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True, default='')
    description = models.TextField(blank=True, default='')
    tech_stack = models.JSONField(default=list, blank=True)
    project_url = models.URLField(blank=True, default='')
    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    is_ongoing = models.BooleanField(default=False)
    is_professional = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_projects'
        ordering = ['order', '-start_year']

    def __str__(self):
        return self.name
