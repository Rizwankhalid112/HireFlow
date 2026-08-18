from rest_framework import serializers

from apps.cv_builder.models import CVSkill, SkillCanonical


class SkillCanonicalSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillCanonical
        fields = ('id', 'canonical_name', 'category', 'is_popular')


class CVSkillSerializer(serializers.ModelSerializer):
    canonical_id = serializers.UUIDField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = CVSkill
        fields = (
            'id',
            'canonical_id',
            'name',
            'category',
            'proficiency',
            'years_of_exp',
            'is_featured',
            'is_verified',
            'order',
            'created_at',
        )
        read_only_fields = ('id', 'is_verified', 'created_at')

    def validate(self, attrs):
        canonical_id = attrs.pop('canonical_id', None)
        if canonical_id:
            try:
                canonical = SkillCanonical.objects.get(id=canonical_id)
            except SkillCanonical.DoesNotExist:
                raise serializers.ValidationError({'canonical_id': 'Canonical skill not found.'})
            attrs['canonical'] = canonical
            attrs['name'] = canonical.canonical_name
            attrs['category'] = canonical.category
            attrs['is_verified'] = True
        elif self.instance and self.instance.canonical_id:
            # Updating an already-matched skill without re-sending canonical_id
            # (e.g. changing only proficiency) must not downgrade it to freetext.
            # canonical_id is write-only, so a client cannot echo it back.
            attrs['name'] = self.instance.canonical.canonical_name
            attrs['category'] = self.instance.canonical.category
            attrs['is_verified'] = True
        else:
            attrs['is_verified'] = False
            if not attrs.get('name'):
                raise serializers.ValidationError({'name': 'Skill name is required.'})
        return attrs


class CVSkillBulkItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    canonical_id = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.CharField(max_length=50, required=False, allow_blank=True)
    proficiency = serializers.CharField(max_length=20, required=False, allow_blank=True)


class CVSkillBulkAddSerializer(serializers.Serializer):
    skills = CVSkillBulkItemSerializer(many=True)
