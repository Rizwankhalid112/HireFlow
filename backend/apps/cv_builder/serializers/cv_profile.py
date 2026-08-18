from rest_framework import serializers

from apps.cv_builder.models import CVProfile
from apps.cv_builder.services.completion import calculate_section_completion
from apps.cv_builder.utils import normalize_profile_url


class CVProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVProfile
        fields = ('id', 'completion_score', 'is_complete')
        read_only_fields = fields


class CVProfileReadSerializer(serializers.ModelSerializer):
    completion_score = serializers.IntegerField(read_only=True)
    is_complete = serializers.BooleanField(read_only=True)
    section_completion = serializers.SerializerMethodField()

    class Meta:
        model = CVProfile
        fields = (
            'id',
            'full_name',
            'professional_title',
            'email',
            'phone',
            'city',
            'country',
            'linkedin_url',
            'github_url',
            'portfolio_url',
            'summary',
            'template_id',
            'completion_score',
            'is_complete',
            'section_completion',
            'content_updated_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'completion_score',
            'is_complete',
            'section_completion',
            'content_updated_at',
            'created_at',
            'updated_at',
        )

    def get_section_completion(self, obj):
        return calculate_section_completion(obj)


class CVProfileWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVProfile
        fields = (
            'full_name',
            'professional_title',
            'email',
            'phone',
            'city',
            'country',
            'linkedin_url',
            'github_url',
            'portfolio_url',
            'summary',
            'template_id',
        )

    def validate_linkedin_url(self, value):
        if value and 'linkedin.com' not in value.lower():
            raise serializers.ValidationError('Must be a LinkedIn URL.')
        return normalize_profile_url(value) if value else value

    def validate_github_url(self, value):
        return normalize_profile_url(value) if value else value

    def validate_portfolio_url(self, value):
        return normalize_profile_url(value) if value else value
