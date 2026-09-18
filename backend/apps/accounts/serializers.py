from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from apps.accounts.errors import AuthMessages
from apps.accounts.models import UserProfile
from apps.accounts.tasks import send_verification_email

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('email', 'full_name', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': AuthMessages.PASSWORDS_DO_NOT_MATCH})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        send_verification_email.delay(str(user.id))
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        request = self.context.get('request')
        user = authenticate(
            request=request,
            username=attrs['email'],
            password=attrs['password'],
        )
        if not user:
            raise serializers.ValidationError(AuthMessages.INVALID_CREDENTIALS)
        if not user.is_active:
            raise serializers.ValidationError(AuthMessages.ACCOUNT_DISABLED)
        if not user.is_email_verified:
            raise serializers.ValidationError(AuthMessages.EMAIL_NOT_VERIFIED)
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id',
            'email',
            'full_name',
            'auth_provider',
            'is_email_verified',
            'date_joined',
        )
        read_only_fields = fields


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    full_name = serializers.CharField(required=False, write_only=True)

    class Meta:
        model = UserProfile
        fields = (
            'user',
            'full_name',
            'avatar',
            'job_title',
            'target_role',
            'target_country',
            'target_salary',
            'linkedin_url',
            'github_url',
            'phone',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('created_at', 'updated_at')

    def update(self, instance, validated_data):
        full_name = validated_data.pop('full_name', None)

        if full_name:
            instance.user.full_name = full_name
            instance.user.save(update_fields=['full_name'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({'old_password': AuthMessages.OLD_PASSWORD_INCORRECT})
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password2': AuthMessages.PASSWORDS_DO_NOT_MATCH})
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password2 = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({'new_password2': AuthMessages.PASSWORDS_DO_NOT_MATCH})
        return attrs
