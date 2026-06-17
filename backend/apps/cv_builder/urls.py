from django.urls import path

from apps.cv_builder.views.cv_profile import CVProfileCompletionView, CVProfileView
from apps.cv_builder.views.education import (
    EducationDetailView,
    EducationListCreateView,
    EducationReorderView,
)
from apps.cv_builder.views.project import (
    CertificationDetailView,
    CertificationListCreateView,
    CertificationReorderView,
    LanguageDetailView,
    LanguageListCreateView,
    LanguageReorderView,
    ProjectDetailView,
    ProjectListCreateView,
    ProjectReorderView,
)
from apps.cv_builder.views.skill import (
    SkillBulkAddView,
    SkillDetailView,
    SkillListCreateView,
    SkillReorderView,
    SkillSearchView,
)
from apps.cv_builder.views.work_experience import (
    WorkBulletDetailView,
    WorkBulletListCreateView,
    WorkBulletReorderView,
    WorkExperienceDetailView,
    WorkExperienceListCreateView,
    WorkExperienceReorderView,
)

urlpatterns = [
    path('profile/', CVProfileView.as_view(), name='cv-profile'),
    path('profile/completion/', CVProfileCompletionView.as_view(), name='cv-profile-completion'),
    path('work-experience/', WorkExperienceListCreateView.as_view(), name='cv-work-experience-list'),
    path('work-experience/reorder/', WorkExperienceReorderView.as_view(), name='cv-work-experience-reorder'),
    path('work-experience/<uuid:pk>/', WorkExperienceDetailView.as_view(), name='cv-work-experience-detail'),
    path(
        'work-experience/<uuid:experience_id>/bullets/',
        WorkBulletListCreateView.as_view(),
        name='cv-work-bullet-list',
    ),
    path(
        'work-experience/<uuid:experience_id>/bullets/reorder/',
        WorkBulletReorderView.as_view(),
        name='cv-work-bullet-reorder',
    ),
    path(
        'work-experience/<uuid:experience_id>/bullets/<uuid:bullet_id>/',
        WorkBulletDetailView.as_view(),
        name='cv-work-bullet-detail',
    ),
    path('education/', EducationListCreateView.as_view(), name='cv-education-list'),
    path('education/reorder/', EducationReorderView.as_view(), name='cv-education-reorder'),
    path('education/<uuid:pk>/', EducationDetailView.as_view(), name='cv-education-detail'),
    path('skills/search/', SkillSearchView.as_view(), name='cv-skill-search'),
    path('skills/bulk-add/', SkillBulkAddView.as_view(), name='cv-skill-bulk-add'),
    path('skills/reorder/', SkillReorderView.as_view(), name='cv-skill-reorder'),
    path('skills/', SkillListCreateView.as_view(), name='cv-skill-list'),
    path('skills/<uuid:pk>/', SkillDetailView.as_view(), name='cv-skill-detail'),
    path('projects/', ProjectListCreateView.as_view(), name='cv-project-list'),
    path('projects/reorder/', ProjectReorderView.as_view(), name='cv-project-reorder'),
    path('projects/<uuid:pk>/', ProjectDetailView.as_view(), name='cv-project-detail'),
    path('certifications/', CertificationListCreateView.as_view(), name='cv-certification-list'),
    path('certifications/reorder/', CertificationReorderView.as_view(), name='cv-certification-reorder'),
    path('certifications/<uuid:pk>/', CertificationDetailView.as_view(), name='cv-certification-detail'),
    path('languages/', LanguageListCreateView.as_view(), name='cv-language-list'),
    path('languages/reorder/', LanguageReorderView.as_view(), name='cv-language-reorder'),
    path('languages/<uuid:pk>/', LanguageDetailView.as_view(), name='cv-language-detail'),
]
