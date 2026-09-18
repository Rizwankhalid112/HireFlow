class AuthMessages:
    PASSWORDS_DO_NOT_MATCH = 'Passwords do not match.'
    INVALID_CREDENTIALS = 'Invalid credentials.'
    ACCOUNT_DISABLED = 'Account is disabled.'
    EMAIL_NOT_VERIFIED = 'Please verify your email first.'
    OLD_PASSWORD_INCORRECT = 'Old password is incorrect.'
    TOKEN_INVALID_OR_EXPIRED = 'Invalid or expired token.'
    USER_NOT_FOUND = 'User not found.'
    REFRESH_TOKEN_NOT_FOUND = 'Refresh token not found.'
    REFRESH_TOKEN_INVALID = 'Invalid or expired refresh token.'
    ACCESS_TOKEN_REQUIRED = 'access_token is required.'
    GITHUB_EMAIL_UNAVAILABLE = 'Unable to retrieve a verified email from GitHub.'


class AuthSuccessMessages:
    REGISTER = 'Check your email to verify your account.'
    LOGOUT = 'Logged out successfully.'
    FORGOT_PASSWORD = "If that email is registered, you'll receive a link."
    PASSWORD_RESET = 'Password reset successfully.'
    PASSWORD_CHANGED = 'Password changed successfully.'
