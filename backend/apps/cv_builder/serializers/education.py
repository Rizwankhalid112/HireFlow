from rest_framework import serializers

from apps.cv_builder.models import Education


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = (
            'id',
            'institution',
            'degree_type',
            'field_of_study',
            'cgpa',
            'cgpa_scale',
            'start_year',
            'end_year',
            'is_current',
            'thesis_title',
            'achievements',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate(self, attrs):
        cgpa = attrs.get('cgpa', getattr(self.instance, 'cgpa', None))
        cgpa_scale = attrs.get('cgpa_scale', getattr(self.instance, 'cgpa_scale', None)) or 4.0

        if cgpa is not None and float(cgpa) > float(cgpa_scale):
            raise serializers.ValidationError({'cgpa': 'CGPA cannot exceed the scale value.'})

        if attrs.get('is_current', getattr(self.instance, 'is_current', False)):
            attrs['end_year'] = None

        return attrs
