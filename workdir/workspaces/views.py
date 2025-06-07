
from django.utils import timezone
from rest_framework import viewsets, permissions
# from drf_spectacular.utils import extend_schema
from .models import Space
from .serializers import SpaceSerializer

class SpaceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Spaces.
    Provides CRUD (Create, Retrieve, Update, Delete) operations for spaces.
    Soft deletion is used for destroying spaces.
    """
    queryset = Space.objects.filter(is_deleted=False)
    serializer_class = SpaceSerializer
    lookup_field = 'key'
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        """Sets the owner of the space to the current authenticated user upon creation."""
        if self.request.user.is_authenticated:
            serializer.save(owner=self.request.user)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        """Soft deletes a space (sets is_deleted=True and records deletion time)."""
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()
