from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.cv_builder.models import (
    CVCertification,
    CVLanguage,
    CVProject,
    CVSkill,
    Education,
    WorkBullet,
    WorkExperience,
)


def _touch_cv_profile(cv):
    if cv:
        cv.touch_content_updated_at()
        cv._update_completion_fields()
        cv.save(update_fields=['is_complete', 'completion_score', 'content_updated_at'])


@receiver(post_save, sender=WorkExperience)
@receiver(post_delete, sender=WorkExperience)
def work_experience_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.cv)


@receiver(post_save, sender=WorkBullet)
@receiver(post_delete, sender=WorkBullet)
def work_bullet_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.experience.cv)


@receiver(post_save, sender=Education)
@receiver(post_delete, sender=Education)
def education_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.cv)


@receiver(post_save, sender=CVSkill)
@receiver(post_delete, sender=CVSkill)
def skill_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.cv)


@receiver(post_save, sender=CVProject)
@receiver(post_delete, sender=CVProject)
def project_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.cv)


@receiver(post_save, sender=CVCertification)
@receiver(post_delete, sender=CVCertification)
def certification_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.cv)


@receiver(post_save, sender=CVLanguage)
@receiver(post_delete, sender=CVLanguage)
def language_changed(sender, instance, **kwargs):
    _touch_cv_profile(instance.cv)
