from rest_framework import serializers

from apps.cv_builder.models import WorkBullet, WorkExperience
from apps.cv_builder.services.metric_extractor import extract_metric
from apps.cv_builder.services.skill_detector import extract_skills_from_bullet


class WorkBulletSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkBullet
        fields = (
            'id',
            'text',
            'impact_metric',
            'skills_demonstrated',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'impact_metric', 'skills_demonstrated', 'created_at')

    def validate_text(self, value):
        if len(value.strip()) < 10:
            raise serializers.ValidationError('Bullet must be at least 10 characters.')
        return value

    def create(self, validated_data):
        validated_data['impact_metric'] = extract_metric(validated_data['text'])
        validated_data['skills_demonstrated'] = extract_skills_from_bullet(validated_data['text'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'text' in validated_data:
            validated_data['impact_metric'] = extract_metric(validated_data['text'])
            validated_data['skills_demonstrated'] = extract_skills_from_bullet(validated_data['text'])
        return super().update(instance, validated_data)


class WorkExperienceSerializer(serializers.ModelSerializer):
    bullets = WorkBulletSerializer(many=True, read_only=True)

    class Meta:
        model = WorkExperience
        fields = (
            'id',
            'company_name',
            'role_title',
            'employment_type',
            'location',
            'location_type',
            'start_month',
            'start_year',
            'end_month',
            'end_year',
            'is_current',
            'order',
            'bullets',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate(self, attrs):
        is_current = attrs.get('is_current', getattr(self.instance, 'is_current', False))
        if is_current:
            attrs['end_month'] = None
            attrs['end_year'] = None
        return attrs
