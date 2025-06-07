from django.db import models
from django.contrib.auth.models import AbstractUser

# For now, we can use the default Django User model.
# If a custom User model is needed later (e.g., extending AbstractUser),
# it would be defined here and DJANGO_AUTH_USER_MODEL updated in settings.
# Example:
# class CustomUser(AbstractUser):
#     # Add any custom fields here
#     pass
