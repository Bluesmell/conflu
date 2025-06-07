from django.contrib.auth.models import User
from rest_framework import generics, permissions
# TokenObtainPairView, TokenRefreshView are not directly used here but imported in urls.py
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import UserRegistrationSerializer

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer
