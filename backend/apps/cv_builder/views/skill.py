from django.db.models import Q

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import CVSkill, SkillCanonical
from apps.cv_builder.serializers.skill import (
    CVSkillBulkAddSerializer,
    CVSkillSerializer,
    SkillCanonicalSearchSerializer,
)
from apps.cv_builder.utils import get_user_cv_profile, reorder_owned_items


class SkillSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return Response([])

        skills = SkillCanonical.objects.filter(
            Q(canonical_name__icontains=query) | Q(aliases__icontains=query),
        ).order_by('-is_popular', 'canonical_name')[:20]
        return Response(SkillCanonicalSearchSerializer(skills, many=True).data)


class SkillListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        skills = CVSkill.objects.filter(cv=profile).select_related('canonical')
        return Response(CVSkillSerializer(skills, many=True).data)

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVSkillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        canonical = validated.get('canonical')
        name = validated['name']

        if canonical:
            existing = CVSkill.objects.filter(cv=profile, canonical=canonical).first()
        else:
            existing = CVSkill.objects.filter(cv=profile, name__iexact=name).first()

        if existing:
            return Response(CVSkillSerializer(existing).data, status=status.HTTP_200_OK)

        skill = serializer.save(cv=profile)
        return Response(CVSkillSerializer(skill).data, status=status.HTTP_201_CREATED)


class SkillDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return CVSkill.objects.get(id=pk, cv__user=request.user)
        except CVSkill.DoesNotExist:
            raise NotFound('Skill not found.')

    def put(self, request, pk):
        skill = self.get_object(request, pk)
        serializer = CVSkillSerializer(skill, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CVSkillSerializer(skill).data)

    def delete(self, request, pk):
        skill = self.get_object(request, pk)
        skill.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class SkillReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ValidationError({'ordered_ids': 'A non-empty list of IDs is required.'})

        try:
            reorder_owned_items(CVSkill, ordered_ids, {'cv__user': request.user})
        except ValueError as exc:
            raise ValidationError({'ordered_ids': str(exc)}) from exc

        profile = get_user_cv_profile(request.user)
        skills = CVSkill.objects.filter(cv=profile)
        return Response(CVSkillSerializer(skills, many=True).data)


class SkillBulkAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = CVSkillBulkAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        added = 0
        skipped = 0

        for item in serializer.validated_data['skills']:
            canonical = None
            if item.get('canonical_id'):
                canonical = SkillCanonical.objects.filter(id=item['canonical_id']).first()

            name = canonical.canonical_name if canonical else item['name']
            defaults = {
                'name': name,
                'category': canonical.category if canonical else item.get('category', ''),
                'proficiency': item.get('proficiency', ''),
                'is_verified': bool(canonical),
            }

            if canonical:
                _, created = CVSkill.objects.get_or_create(
                    cv=profile,
                    canonical=canonical,
                    defaults=defaults,
                )
            else:
                _, created = CVSkill.objects.get_or_create(
                    cv=profile,
                    name=name,
                    defaults=defaults,
                )

            if created:
                added += 1
            else:
                skipped += 1

        return Response({'added': added, 'skipped': skipped})
