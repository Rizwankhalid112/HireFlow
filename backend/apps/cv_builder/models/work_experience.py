import uuid

from django.db import models

from apps.cv_builder.models.cv_profile import CVProfile


class WorkExperience(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full-time'
        PART_TIME = 'part_time', 'Part-time'
        INTERNSHIP = 'internship', 'Internship'
        CONTRACT = 'contract', 'Contract'
        FREELANCE = 'freelance', 'Freelance'

    class LocationType(models.TextChoices):
        ONSITE = 'onsite', 'Onsite'
        REMOTE = 'remote', 'Remote'
        HYBRID = 'hybrid', 'Hybrid'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='work_experiences',
    )
    company_name = models.CharField(max_length=200)
    role_title = models.CharField(max_length=200)
    employment_type = models.CharField(
        max_length=50,
        choices=EmploymentType.choices,
        blank=True,
        default='',
    )
    location = models.CharField(max_length=200, blank=True, default='')
    location_type = models.CharField(
        max_length=20,
        choices=LocationType.choices,
        blank=True,
        default='',
    )
    start_month = models.IntegerField(null=True, blank=True)
    start_year = models.IntegerField()
    end_month = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_work_experiences'
        ordering = ['order', '-start_year', '-start_month']

    def __str__(self):
        return f'{self.role_title} at {self.company_name}'


class WorkBullet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    experience = models.ForeignKey(
        WorkExperience,
        on_delete=models.CASCADE,
        related_name='bullets',
    )
    text = models.TextField()
    impact_metric = models.CharField(max_length=255, null=True, blank=True)
    skills_demonstrated = models.JSONField(default=list, blank=True)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_work_bullets'
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.text[:80]
