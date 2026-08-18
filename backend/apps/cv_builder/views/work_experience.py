from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cv_builder.models import WorkBullet, WorkExperience
from apps.cv_builder.serializers.work_experience import WorkBulletSerializer, WorkExperienceSerializer
from apps.cv_builder.utils import get_user_cv_profile, reorder_owned_items


class WorkExperienceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = get_user_cv_profile(request.user)
        experiences = WorkExperience.objects.filter(cv=profile).prefetch_related('bullets')
        return Response(WorkExperienceSerializer(experiences, many=True).data)

    def post(self, request):
        profile = get_user_cv_profile(request.user)
        serializer = WorkExperienceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        experience = serializer.save(cv=profile)
        return Response(WorkExperienceSerializer(experience).data, status=status.HTTP_201_CREATED)


class WorkExperienceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        try:
            return WorkExperience.objects.prefetch_related('bullets').get(
                id=pk,
                cv__user=request.user,
            )
        except WorkExperience.DoesNotExist:
            raise NotFound('Work experience not found.')

    def put(self, request, pk):
        experience = self.get_object(request, pk)
        serializer = WorkExperienceSerializer(experience, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(WorkExperienceSerializer(experience).data)

    def delete(self, request, pk):
        experience = self.get_object(request, pk)
        experience.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkExperienceReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ValidationError({'ordered_ids': 'A non-empty list of IDs is required.'})

        try:
            reorder_owned_items(
                WorkExperience,
                ordered_ids,
                {'cv__user': request.user},
            )
        except ValueError as exc:
            raise ValidationError({'ordered_ids': str(exc)}) from exc

        profile = get_user_cv_profile(request.user)
        experiences = WorkExperience.objects.filter(cv=profile).prefetch_related('bullets')
        return Response(WorkExperienceSerializer(experiences, many=True).data)


class WorkBulletListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_experience(self, request, experience_id):
        try:
            return WorkExperience.objects.get(id=experience_id, cv__user=request.user)
        except WorkExperience.DoesNotExist:
            raise NotFound('Work experience not found.')

    def get(self, request, experience_id):
        experience = self.get_experience(request, experience_id)
        bullets = experience.bullets.all()
        return Response(WorkBulletSerializer(bullets, many=True).data)

    def post(self, request, experience_id):
        experience = self.get_experience(request, experience_id)
        serializer = WorkBulletSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bullet = serializer.save(experience=experience)
        return Response(WorkBulletSerializer(bullet).data, status=status.HTTP_201_CREATED)


class WorkBulletDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_bullet(self, request, experience_id, bullet_id):
        try:
            return WorkBullet.objects.get(
                id=bullet_id,
                experience_id=experience_id,
                experience__cv__user=request.user,
            )
        except WorkBullet.DoesNotExist:
            raise NotFound('Bullet not found.')

    def put(self, request, experience_id, bullet_id):
        bullet = self.get_bullet(request, experience_id, bullet_id)
        serializer = WorkBulletSerializer(bullet, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(WorkBulletSerializer(bullet).data)

    def delete(self, request, experience_id, bullet_id):
        bullet = self.get_bullet(request, experience_id, bullet_id)
        bullet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WorkBulletReorderView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, experience_id):
        ordered_ids = request.data.get('ordered_ids')
        if not isinstance(ordered_ids, list) or not ordered_ids:
            raise ValidationError({'ordered_ids': 'A non-empty list of IDs is required.'})

        try:
            reorder_owned_items(
                WorkBullet,
                ordered_ids,
                {
                    'experience_id': experience_id,
                    'experience__cv__user': request.user,
                },
            )
        except ValueError as exc:
            raise ValidationError({'ordered_ids': str(exc)}) from exc

        bullets = WorkBullet.objects.filter(
            experience_id=experience_id,
            experience__cv__user=request.user,
        )
        return Response(WorkBulletSerializer(bullets, many=True).data)
