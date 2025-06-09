from django.contrib.auth.models import User
from rest_framework import generics, permissions
# TokenObtainPairView, TokenRefreshView are not directly used here but imported in urls.py
# from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
# from .serializers import UserRegistrationSerializer # Commented out as UserRegistrationView is removed

#class UserRegistrationView(generics.CreateAPIView):
#    queryset = User.objects.all()
#    permission_classes = (permissions.AllowAny,)
#    serializer_class = UserRegistrationSerializer

from django.contrib.auth.models import Group # For GroupListView
from .serializers import UserSimpleSerializer, GroupSerializer # GroupSerializer will be created

class UserListView(generics.ListAPIView):
    """
    Provides a list of users (id, username, email, first_name, last_name).
    Requires authentication.
    """
    queryset = User.objects.all().order_by('username')
    serializer_class = UserSimpleSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupListView(generics.ListAPIView):
    """
    Provides a list of groups (id, name).
    Requires authentication.
    """
    queryset = Group.objects.all().order_by('name')
    serializer_class = GroupSerializer # To be created in serializers.py
    permission_classes = [permissions.IsAuthenticated]
