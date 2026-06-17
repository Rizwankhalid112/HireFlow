import uuid

from django.db import models

from apps.cv_builder.models.cv_profile import CVProfile


class Education(models.Model):
    class DegreeType(models.TextChoices):
        BS = 'bs', 'BS'
        MS = 'ms', 'MS'
        PHD = 'phd', 'PhD'
        DIPLOMA = 'diploma', 'Diploma'
        CERTIFICATE = 'certificate', 'Certificate'
        OTHER = 'other', 'Other'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='education_entries',
    )
    institution = models.CharField(max_length=300)
    degree_type = models.CharField(
        max_length=50,
        choices=DegreeType.choices,
        blank=True,
        default='',
    )
    field_of_study = models.CharField(max_length=200, blank=True, default='')
    cgpa = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    cgpa_scale = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    start_year = models.IntegerField()
    end_year = models.IntegerField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    thesis_title = models.TextField(blank=True, default='')
    achievements = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_education'
        ordering = ['order', '-start_year']
        verbose_name_plural = 'education entries'

    def __str__(self):
        return f'{self.degree_type} — {self.institution}'
