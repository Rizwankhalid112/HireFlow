from rest_framework import serializers

from apps.cv_builder.models import CVCertification, CVLanguage, CVProject


class CVProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVProject
        fields = (
            'id',
            'name',
            'subtitle',
            'description',
            'tech_stack',
            'project_url',
            'start_year',
            'end_year',
            'is_ongoing',
            'is_professional',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_tech_stack(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError('tech_stack must be a list.')
        if len(value) > 10:
            raise serializers.ValidationError('Maximum 10 technologies per project.')
        if not all(isinstance(item, str) for item in value):
            raise serializers.ValidationError('All tech_stack items must be strings.')
        return value


class CVCertificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVCertification
        fields = (
            'id',
            'name',
            'issuing_organization',
            'issue_month',
            'issue_year',
            'expiry_year',
            'credential_url',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')


class CVLanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVLanguage
        fields = (
            'id',
            'language_name',
            'proficiency',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')
