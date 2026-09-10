import uuid

from django.db import models

from apps.accounts.models import User
from apps.cv_builder.templates_registry import DEFAULT_TEMPLATE_ID, template_choices


class CVProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cv_profile',
    )
    full_name = models.CharField(max_length=100, blank=True, default='')
    professional_title = models.CharField(max_length=150, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    phone = models.CharField(max_length=30, blank=True, default='')
    city = models.CharField(max_length=100, blank=True, default='')
    country = models.CharField(max_length=100, blank=True, default='')
    linkedin_url = models.URLField(blank=True, default='')
    github_url = models.URLField(blank=True, default='')
    portfolio_url = models.URLField(blank=True, default='')
    summary = models.TextField(blank=True, default='')
    # Defaulted rather than nullable: the live preview always has a template to
    # render, so "no template chosen yet" is not a state anything downstream
    # handles — the picker would show nothing selected and the renderer would
    # silently fall back.
    template_id = models.CharField(
        max_length=50,
        default=DEFAULT_TEMPLATE_ID,
        choices=template_choices(),
    )
    photo = models.ImageField(upload_to='cv_photos/%Y/%m/', null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    completion_score = models.IntegerField(default=0)
    content_updated_at = models.DateTimeField(auto_now=True)
    pdf_file = models.FileField(upload_to='cv_pdfs/%Y/%m/', null=True, blank=True)
    pdf_generated_at = models.DateTimeField(null=True, blank=True)
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cv_profiles'
        ordering = ['-updated_at']

    def __str__(self):
        return f'CVProfile for {self.user.email}'

    def save(self, *args, **kwargs):
        self._update_completion_fields()
        super().save(*args, **kwargs)

    def _update_completion_fields(self):
        from apps.cv_builder.services.completion import compute_completion

        score, is_complete = compute_completion(self)
        self.completion_score = score
        self.is_complete = is_complete

    def touch_content_updated_at(self):
        from django.utils import timezone

        CVProfile.objects.filter(pk=self.pk).update(content_updated_at=timezone.now())
