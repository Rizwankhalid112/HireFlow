import io

from django.core.files.uploadedfile import InMemoryUploadedFile

from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from apps.cv_builder.models import CVProfile

MAX_UPLOAD_BYTES = 2 * 1024 * 1024  # 2 MB
MAX_DIMENSION = 600
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}


class CVPhotoSerializer(serializers.ModelSerializer):
    photo = serializers.ImageField(required=True)

    class Meta:
        model = CVProfile
        fields = ('photo',)

    def validate_photo(self, image):
        # nginx allows 20 MB, so the real ceiling has to be enforced here.
        if image.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError('Photo must be 2 MB or smaller.')

        # Decide by decoding, never by file extension.
        try:
            probe = Image.open(image)
            probe.verify()
        except (UnidentifiedImageError, OSError) as exc:
            raise serializers.ValidationError('That file is not a valid image.') from exc

        if probe.format not in ALLOWED_FORMATS:
            raise serializers.ValidationError('Use a JPEG, PNG or WebP image.')

        # verify() leaves the file unusable, so reopen to actually process it.
        image.seek(0)
        source = Image.open(image)

        # Re-encoding through a fresh canvas drops EXIF, which routinely carries
        # GPS coordinates on phone photos. A CV gets emailed to strangers, so
        # this is done unconditionally rather than only when resizing.
        source = source.convert('RGB')
        source.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        buffer = io.BytesIO()
        source.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)

        return InMemoryUploadedFile(
            buffer,
            field_name='photo',
            name='cv-photo.jpg',
            content_type='image/jpeg',
            size=buffer.getbuffer().nbytes,
            charset=None,
        )

    def update(self, instance, validated_data):
        # Replace rather than accumulate orphans in media storage.
        if instance.photo:
            instance.photo.delete(save=False)
        return super().update(instance, validated_data)
