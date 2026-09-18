from django.contrib import admin

from apps.cv_builder.models import (
    CVCertification,
    CVLanguage,
    CVProfile,
    CVProject,
    CVSkill,
    CVUploadLog,
    Education,
    SkillCanonical,
    WorkBullet,
    WorkExperience,
)


class WorkBulletInline(admin.TabularInline):
    model = WorkBullet
    extra = 0
    fields = ('text', 'impact_metric', 'order')


@admin.register(CVProfile)
class CVProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'full_name',
        'professional_title',
        'is_complete',
        'completion_score',
        'content_updated_at',
        'updated_at',
    )
    list_filter = ('is_complete', 'reminder_sent')
    search_fields = ('user__email', 'full_name', 'professional_title', 'email')
    readonly_fields = (
        'is_complete',
        'completion_score',
        'content_updated_at',
        'created_at',
        'updated_at',
        'pdf_generated_at',
    )


@admin.register(WorkExperience)
class WorkExperienceAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'role_title', 'cv', 'is_current', 'start_year', 'order')
    list_filter = ('employment_type', 'location_type', 'is_current')
    search_fields = ('company_name', 'role_title', 'cv__user__email')
    inlines = [WorkBulletInline]


@admin.register(WorkBullet)
class WorkBulletAdmin(admin.ModelAdmin):
    list_display = ('experience', 'text', 'impact_metric', 'order')
    search_fields = ('text', 'experience__company_name')


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('institution', 'degree_type', 'field_of_study', 'cv', 'start_year', 'order')
    list_filter = ('degree_type', 'is_current')
    search_fields = ('institution', 'field_of_study', 'cv__user__email')


@admin.register(SkillCanonical)
class SkillCanonicalAdmin(admin.ModelAdmin):
    list_display = ('canonical_name', 'category', 'is_popular')
    list_filter = ('category', 'is_popular')
    search_fields = ('canonical_name',)


@admin.register(CVSkill)
class CVSkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'cv', 'category', 'proficiency', 'is_featured', 'is_verified', 'order')
    list_filter = ('proficiency', 'is_featured', 'is_verified', 'category')
    search_fields = ('name', 'cv__user__email')


@admin.register(CVProject)
class CVProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'cv', 'is_professional', 'is_ongoing', 'start_year', 'order')
    list_filter = ('is_professional', 'is_ongoing')
    search_fields = ('name', 'subtitle', 'cv__user__email')


@admin.register(CVCertification)
class CVCertificationAdmin(admin.ModelAdmin):
    list_display = ('name', 'issuing_organization', 'cv', 'issue_year', 'expiry_year', 'order')
    search_fields = ('name', 'issuing_organization', 'cv__user__email')


@admin.register(CVLanguage)
class CVLanguageAdmin(admin.ModelAdmin):
    list_display = ('language_name', 'proficiency', 'cv', 'order')
    list_filter = ('proficiency',)
    search_fields = ('language_name', 'cv__user__email')


@admin.register(CVUploadLog)
class CVUploadLogAdmin(admin.ModelAdmin):
    list_display = (
        'original_filename',
        'cv',
        'file_type',
        'parse_status',
        'fields_extracted',
        'fields_total',
        'uploaded_at',
    )
    list_filter = ('file_type', 'parse_status')
    search_fields = ('original_filename', 'cv__user__email', 'error_message')
    readonly_fields = ('uploaded_at', 'extracted_at', 'parsed_at')
