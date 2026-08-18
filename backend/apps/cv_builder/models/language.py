import uuid

from django.db import models

from apps.cv_builder.models.cv_profile import CVProfile


class CVLanguage(models.Model):
    class Proficiency(models.TextChoices):
        NATIVE = 'native', 'Native'
        FLUENT = 'fluent', 'Fluent'
        PROFESSIONAL = 'professional', 'Professional'
        BASIC = 'basic', 'Basic'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='languages',
    )
    language_name = models.CharField(max_length=100)
    proficiency = models.CharField(
        max_length=20,
        choices=Proficiency.choices,
        blank=True,
        default='',
    )
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_languages'
        ordering = ['order', 'language_name']

    def __str__(self):
        return f'{self.language_name} ({self.proficiency})'
