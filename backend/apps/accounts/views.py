from django.contrib.auth import get_user_model
from django.core.signing import BadSignature, SignatureExpired, loads
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.cookies import (
    clear_refresh_cookie,
    get_refresh_token_from_cookie,
    set_refresh_cookie,
)
from apps.accounts.errors import AuthMessages, AuthSuccessMessages
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserProfileSerializer,
)
from apps.accounts.social import perform_github_login, perform_google_login
from apps.accounts.tasks import RESET_SALT, VERIFY_SALT, send_password_reset_email

User = get_user_model()

VERIFY_MAX_AGE = 86400
RESET_MAX_AGE = 3600


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'message': AuthSuccessMessages.REGISTER},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, token):
        try:
            data = loads(token, salt=VERIFY_SALT, max_age=VERIFY_MAX_AGE)
            user = User.objects.get(id=data['user_id'])
        except (BadSignature, SignatureExpired):
            return Response({'detail': AuthMessages.TOKEN_INVALID_OR_EXPIRED}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'detail': AuthMessages.USER_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        user.is_email_verified = True
        user.save(update_fields=['is_email_verified'])

        refresh = RefreshToken.for_user(user)
        response = Response({'access': str(refresh.access_token)}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, refresh)
        return response


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        refresh = RefreshToken.for_user(user)
        response = Response({'access': str(refresh.access_token)}, status=status.HTTP_200_OK)
        set_refresh_cookie(response, refresh)
        return response


class LogoutView(APIView):
    def post(self, request):
        refresh_token = get_refresh_token_from_cookie(request)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        response = Response({'message': AuthSuccessMessages.LOGOUT}, status=status.HTTP_200_OK)
        clear_refresh_cookie(response)
        return response


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = get_refresh_token_from_cookie(request)
        if not refresh_token:
            return Response({'detail': AuthMessages.REFRESH_TOKEN_NOT_FOUND}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            refresh = RefreshToken(refresh_token)
            user = User.objects.get(id=refresh['user_id'])
            refresh.blacklist()
            new_refresh = RefreshToken.for_user(user)
            response = Response(
                {'access': str(new_refresh.access_token)},
                status=status.HTTP_200_OK,
            )
            set_refresh_cookie(response, new_refresh)
            return response
        except (TokenError, User.DoesNotExist):
            return Response(
                {'detail': AuthMessages.REFRESH_TOKEN_INVALID},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = User.objects.filter(email__iexact=serializer.validated_data['email']).first()
        if user:
            send_password_reset_email.delay(str(user.id))

        return Response(
            {'message': AuthSuccessMessages.FORGOT_PASSWORD},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            data = loads(
                serializer.validated_data['token'],
                salt=RESET_SALT,
                max_age=RESET_MAX_AGE,
            )
            user = User.objects.get(id=data['user_id'])
        except (BadSignature, SignatureExpired):
            return Response({'detail': AuthMessages.TOKEN_INVALID_OR_EXPIRED}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'detail': AuthMessages.USER_NOT_FOUND}, status=status.HTTP_404_NOT_FOUND)

        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response({'message': AuthSuccessMessages.PASSWORD_RESET}, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    def get(self, request):
        serializer = UserProfileSerializer(request.user.profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        profile = request.user.profile
        serializer = UserProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': AuthSuccessMessages.PASSWORD_CHANGED}, status=status.HTTP_200_OK)


class GoogleLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return perform_google_login(request)


class GitHubLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return perform_github_login(request)
