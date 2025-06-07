

## User Account Management Update
User account management is now handled by `django-allauth` for core logic
(email verification, password reset flows, etc.) and `dj-rest-auth` for
providing API endpoints for these features (registration, login, logout,
password reset, email confirmation).

Key functionalities include:
- User registration with mandatory email verification.
- Login via username or email.
- Password reset via email.
- API endpoints under `/api/v1/auth/` and `/api/v1/auth/registration/`.

The previous custom registration view has been disabled.
