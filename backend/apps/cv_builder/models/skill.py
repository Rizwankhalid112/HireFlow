import uuid

from django.db import models

from apps.cv_builder.models.cv_profile import CVProfile


class SkillCanonical(models.Model):
    class Category(models.TextChoices):
        LANGUAGES = 'Languages', 'Languages'
        FRAMEWORKS = 'Frameworks', 'Frameworks'
        DATABASES = 'Databases', 'Databases'
        TOOLS = 'Tools', 'Tools'
        CONCEPTS = 'Concepts', 'Concepts'
        CLOUD = 'Cloud', 'Cloud'
        SOFT_SKILLS = 'Soft Skills', 'Soft Skills'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_name = models.CharField(max_length=100, unique=True)
    aliases = models.JSONField(default=list, blank=True)
    category = models.CharField(max_length=50, choices=Category.choices)
    logo_url = models.URLField(null=True, blank=True)
    is_popular = models.BooleanField(default=False)

    class Meta:
        db_table = 'cv_skill_canonical'
        ordering = ['category', 'canonical_name']

    def __str__(self):
        return self.canonical_name


class CVSkill(models.Model):
    class Proficiency(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        EXPERT = 'expert', 'Expert'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cv = models.ForeignKey(
        CVProfile,
        on_delete=models.CASCADE,
        related_name='skills',
    )
    canonical = models.ForeignKey(
        SkillCanonical,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cv_skills',
    )
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, blank=True, default='')
    proficiency = models.CharField(
        max_length=20,
        choices=Proficiency.choices,
        blank=True,
        default='',
    )
    years_of_exp = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cv_skills'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
