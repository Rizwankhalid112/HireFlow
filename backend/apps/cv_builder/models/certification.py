import uuid

from django.db import models

from apps.cv_builder.models.cv_profile import CVProfile


class CVCertification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='certifications',
    )
    name = models.CharField(max_length=300)
    issuing_organization = models.CharField(max_length=300, blank=True, default='')
    issue_month = models.IntegerField(null=True, blank=True)
    issue_year = models.IntegerField(null=True, blank=True)
    expiry_year = models.IntegerField(null=True, blank=True)
    credential_url = models.URLField(blank=True, default='')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_certifications'
        ordering = ['order', '-issue_year', '-issue_month']

    def __str__(self):
        return self.name
