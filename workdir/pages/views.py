from django.utils import timezone
from django.db import transaction
# from django.shortcuts import get_object_or_404 # Not directly used, but common
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer
from guardian.shortcuts import assign_perm
from .models import Page, PageVersion, Tag
# Removed Space import, not directly used here. Workspace/Space imported in serializers.py

# Updated serializer imports
from .serializers import PageSerializer, PageVersionSerializer, TagSerializer, PageDetailSerializer
from core.permissions import ExtendedDjangoObjectPermissionsOrAnonReadOnly

# New imports for PageDetailView
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly


class PageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Pages.
    Provides CRUD operations, versioning, and tagging for pages.
    """
    # Page model does not have is_deleted, so filter removed.
    # Added prefetch for children as it's often useful for list/detail.
    queryset = Page.objects.all().prefetch_related('tags', 'children').select_related('author', 'space', 'space__workspace', 'parent')
    serializer_class = PageSerializer # Use the CRUD-capable PageSerializer
    permission_classes = [ExtendedDjangoObjectPermissionsOrAnonReadOnly]

    def perform_create(self, serializer):
        with transaction.atomic():
            page = serializer.save(author=self.request.user, version=1) # Slug auto-generated in model's save()
            user = self.request.user
            assign_perm('pages.view_page', user, page)
            assign_perm('pages.change_page', user, page)
            assign_perm('pages.delete_page', user, page)

            page_content_for_version = serializer.validated_data.get('content_json', {})

            PageVersion.objects.create(
                page=page,
                version_number=1,
                content_json=page_content_for_version,
                schema_version=serializer.validated_data.get('schema_version', 1),
                author=user,
                commit_message="Initial version."
            )

    @extend_schema(
        request=PageSerializer,
        responses={200: PageSerializer},
        description="Updates a page and creates a new version. A 'commit_message' (string, optional) can be provided in the request body."
    )
    def perform_update(self, serializer):
        with transaction.atomic():
            page_instance = serializer.instance
            new_version_number = page_instance.version + 1

            # content_json is directly part of the Page model and serializer handles its update
            updated_page = serializer.save(version=new_version_number) # Slug will be preserved or updated via model's save if logic allows
            user = self.request.user

            commit_message = self.request.data.get('commit_message', f'Version {new_version_number}.')
            PageVersion.objects.create(
                page=updated_page,
                version_number=new_version_number, # Corrected variable name
                content_json=updated_page.content_json,
                schema_version=updated_page.schema_version,
                author=user,
                commit_message=commit_message
            )

    def perform_destroy(self, instance):
        # Page model does not have is_deleted field. This will perform a hard delete.
        instance.delete()


    @extend_schema(
        request=inline_serializer(
            name='PageTagAddRequest',
            fields={'tag': serializers.CharField(help_text="Name or ID of the tag to add.")}
        ),
        responses={200: PageSerializer}, # Use PageSerializer
        description="Adds a tag to the page. Tag can be specified by ID or name (creates if name doesn't exist). Requires 'pages.change_page' object permission."
    )
    @action(detail=True, methods=['post'], url_path='tags', permission_classes=[ExtendedDjangoObjectPermissionsOrAnonReadOnly])
    def add_page_tag(self, request, pk=None):
        page = self.get_object()
        tag_name_or_id = request.data.get('tag')
        if not tag_name_or_id:
            return Response({'error': 'Tag name or ID must be provided in "tag" field.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            if isinstance(tag_name_or_id, int) or str(tag_name_or_id).isdigit():
                tag = Tag.objects.get(pk=tag_name_or_id)
            else:
                tag, created = Tag.objects.get_or_create(name=str(tag_name_or_id).lower())
        except Tag.DoesNotExist:
            return Response({'error': f'Tag "{tag_name_or_id}" not found.'}, status=status.HTTP_404_NOT_FOUND)
        page.tags.add(tag)
        return Response(PageSerializer(page, context={'request': request}).data, status=status.HTTP_200_OK)


    @extend_schema(
        parameters=[OpenApiParameter(name="tag_pk_or_name", description="Primary key or name of the tag to remove.", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.PATH)],
        responses={200: PageSerializer}, # Use PageSerializer
        description="Removes a tag from the page. Requires 'pages.change_page' object permission."
    )
    @action(detail=True, methods=['delete'], url_path='tags/(?P<tag_pk_or_name>[^/.]+)', permission_classes=[ExtendedDjangoObjectPermissionsOrAnonReadOnly])
    def remove_page_tag(self, request, pk=None, tag_pk_or_name=None):
        page = self.get_object()
        if not request.user.has_perm('pages.change_page', page): # Explicit permission check
             return Response({'detail': 'You do not have permission to change this page.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            if str(tag_pk_or_name).isdigit():
                tag = Tag.objects.get(pk=tag_pk_or_name)
            else:
                tag = Tag.objects.get(name=str(tag_pk_or_name).lower())
        except Tag.DoesNotExist:
            return Response({'error': f'Tag "{tag_pk_or_name}" not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not page.tags.filter(pk=tag.pk).exists():
            return Response({'error': f'Tag "{tag_pk_or_name}" is not associated with this page.'}, status=status.HTTP_400_BAD_REQUEST)
        page.tags.remove(tag)
        return Response(PageSerializer(page, context={'request': request}).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=inline_serializer(
            name='PageRevertRequest',
            fields={'commit_message': serializers.CharField(required=False, help_text="Optional commit message for the revert action.")}
        ),
        parameters=[OpenApiParameter(name="version_number_str", description="The version number to revert to.", required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)],
        responses={200: PageSerializer}, # Use PageSerializer
        description="Reverts the page to a specified previous version. This creates a new version reflecting the reverted state. Requires 'pages.change_page' object permission."
    )
    @action(detail=True, methods=['post'], url_path='revert/(?P<version_number_str>[0-9]+)', permission_classes=[ExtendedDjangoObjectPermissionsOrAnonReadOnly])
    def revert(self, request, pk=None, version_number_str=None):
        page = self.get_object()
        try:
            version_number_to_revert_to = int(version_number_str)
            target_version = PageVersion.objects.get(page=page, version_number=version_number_to_revert_to)
        except PageVersion.DoesNotExist:
            return Response({'error': f'Version {version_number_str} not found for this page.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Invalid version number format.'}, status=status.HTTP_400_BAD_REQUEST)

        if page.content_json == target_version.content_json and page.schema_version == target_version.schema_version:
             return Response({'message': 'Page content is already identical to this version.'}, status=status.HTTP_200_OK)

        with transaction.atomic():
            page.content_json = target_version.content_json
            page.schema_version = target_version.schema_version
            new_current_version_number = page.version + 1
            page.version = new_current_version_number
            page.save()

            PageVersion.objects.create(
                page=page,
                version_number=new_current_version_number,
                content_json=page.content_json,
                schema_version=page.schema_version,
                author=request.user,
                commit_message=request.data.get('commit_message', f'Reverted to version {version_number_to_revert_to}.')
            )
        return Response(PageSerializer(page, context={'request': request}).data, status=status.HTTP_200_OK)


class PageVersionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PageVersion.objects.all().select_related('page', 'author')
    serializer_class = PageVersionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


# --- New PageDetailView ---
class PageDetailView(RetrieveAPIView):
    """
    API view to retrieve a single Page instance with detailed nested data.
    """
    queryset = Page.objects.all().select_related( # Updated to Page.objects.all()
        'space', 'space__workspace', 'parent', 'imported_by', 'author' # Added author
    ).prefetch_related(
        'children', 'page_specific_attachments', 'tags' # Added tags
    )
    serializer_class = PageDetailSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'slug' # Changed from 'pk' to 'slug'
