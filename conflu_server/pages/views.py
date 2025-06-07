from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Space, Page, PageVersion # Added PageVersion
from .serializers import SpaceSerializer, PageSerializer, PageVersionSerializer # Added PageVersionSerializer

class SpaceViewSet(viewsets.ModelViewSet):
    queryset = Space.objects.filter(is_deleted=False) # Only show non-deleted spaces
    serializer_class = SpaceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # ReadOnly for unauthenticated, R/W for authenticated
    lookup_field = 'key' # Use 'key' for retrieving spaces

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    # Soft delete for spaces
    def perform_destroy(self, instance):
        instance.is_deleted = True
        # instance.deleted_at = timezone.now() # Requires timezone import
        from django.utils import timezone # Import timezone
        instance.deleted_at = timezone.now()
        instance.save()

class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.filter(is_deleted=False)
    serializer_class = PageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        # Ensure space exists and user has permission to create page in it (simplified for now)
        # Versioning logic will also go here or in model's save()
        # Space object is expected to be passed by ID in serializer.validated_data['space']
        serializer.save(author=self.request.user, version=1)
        # Create initial PageVersion
        page_instance = serializer.instance
        PageVersion.objects.create(
            page=page_instance,
            version_number=1,
            raw_content=page_instance.raw_content,
            schema_version=page_instance.schema_version,
            author=self.request.user,
            commit_message="Initial version."
        )


    def perform_update(self, serializer):
        # More complex logic for versioning on update will be added later
        # For now, simple update that bumps version and creates new PageVersion
        instance = serializer.instance
        new_version_number = instance.version + 1

        # Save new page content
        serializer.save(author=self.request.user, version=new_version_number)

        # Create new PageVersion
        PageVersion.objects.create(
            page=instance,
            version_number=new_version_number,
            raw_content=serializer.validated_data.get('raw_content', instance.raw_content),
            schema_version=serializer.validated_data.get('schema_version', instance.schema_version),
            author=self.request.user,
            commit_message=self.request.data.get('commit_message', f"Updated to v{new_version_number}")
        )

    # Soft delete for pages
    def perform_destroy(self, instance):
        instance.is_deleted = True
        from django.utils import timezone # Import timezone
        instance.deleted_at = timezone.now()
        instance.save()

# Optional: A ViewSet for PageVersions if direct manipulation is needed
# For now, PageVersions are managed through PageViewSet create/update
# class PageVersionViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = PageVersion.objects.all().order_by('-page_id', '-version_number')
#     serializer_class = PageVersionSerializer
#     permission_classes = [permissions.IsAuthenticated] # Or more specific permissions
#
#     # Example: Filter by page_id
#     # def get_queryset(self):
#     #     queryset = super().get_queryset()
#     #     page_id = self.request.query_params.get('page_id')
#     #     if page_id:
#     #         queryset = queryset.filter(page_id=page_id)
#     #     return queryset
