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


class SchemelessURLField(serializers.URLField):
    """A URLField that accepts what people actually type.

    CVs and humans write `linkedin.com/in/you`, and DRF's `URLField` rejects it
    with "Enter a valid URL" — inside `to_internal_value()`, which runs *before*
    `validate_<field>()`, so the normalizer that was supposed to fix it never
    saw the value. That made `normalize_profile_url` dead code on this path and
    is why the frontend has to prepend `https://` itself.

    Normalising here, before validation, fixes it for every caller — the form,
    Postman, and the CV import, which already accepted scheme-less URLs and so
    disagreed with this endpoint about the same input.
    """

    def to_internal_value(self, data):
        if isinstance(data, str) and data.strip():
            data = normalize_profile_url(data)
        return super().to_internal_value(data)


class CVProfileWriteSerializer(serializers.ModelSerializer):
    linkedin_url = SchemelessURLField(required=False, allow_blank=True)
    github_url = SchemelessURLField(required=False, allow_blank=True)
    portfolio_url = SchemelessURLField(required=False, allow_blank=True)

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
        # The scheme is already normalised by the field above, so this is only
        # the domain check.
        if value and 'linkedin.com' not in value.lower():
            raise serializers.ValidationError('Must be a LinkedIn URL.')
        return value
