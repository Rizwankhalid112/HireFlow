from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    ForgotPasswordView,
    GitHubLoginView,
    GoogleLoginView,
    LoginView,
    LogoutView,
    RegisterView,
    ResetPasswordView,
    TokenRefreshView,
    UserProfileView,
    VerifyEmailView,
)

auth_urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/<str:token>/', VerifyEmailView.as_view(), name='verify-email'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('google/', GoogleLoginView.as_view(), name='google-login'),
    path('github/', GitHubLoginView.as_view(), name='github-login'),
]

user_urlpatterns = [
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
]
