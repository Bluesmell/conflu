
from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse, inline_serializer
from .models import Page, PageVersion, Tag
from .serializers import PageSerializer, PageVersionSerializer, TagSerializer

class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.filter(is_deleted=False).prefetch_related('tags').select_related('author', 'space')
    serializer_class = PageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        with transaction.atomic():
            page_author = self.request.user if self.request.user.is_authenticated else None
            page = serializer.save(author=page_author, version=1) # space comes from validated_data
            PageVersion.objects.create(
                page=page, version_number=1,
                raw_content=serializer.validated_data.get('raw_content', {}),
                schema_version=serializer.validated_data.get('schema_version', 1),
                author=page_author, commit_message="Initial version."
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            page_instance = serializer.instance
            new_version_number = page_instance.version + 1

            # Preserve original space if client doesn't send it, or if we want to make it immutable on update
            # If 'space' is not in serializer.validated_data, serializer.save() keeps original.
            # If client sends 'space', it will be in validated_data.
            # To prevent space update: original_space = page_instance.space
            # Then: updated_page = serializer.save(space=original_space)
            # For now, allow space update if client provides it and it's valid.

            updated_page = serializer.save()
            updated_page.version = new_version_number
            updated_page.save(update_fields=['version', 'updated_at'])

            version_author = self.request.user if self.request.user.is_authenticated else None
            commit_message = self.request.data.get('commit_message', f'Version {new_version_number}.')
            PageVersion.objects.create(
                page=updated_page, version_number=new_version_number,
                raw_content=updated_page.raw_content, schema_version=updated_page.schema_version,
                author=version_author, commit_message=commit_message
            )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()

    @action(detail=True, methods=['post'], url_path='tags', permission_classes=[permissions.IsAuthenticated])
    def manage_tags_add(self, request, pk=None):
        page = self.get_object()
        tag_name_or_id = request.data.get('tag')
        if not tag_name_or_id: return Response({'error': 'Tag name or ID must be provided.'}, status=status.HTTP_400_BAD_REQUEST)
        try: tag = Tag.objects.get(pk=tag_name_or_id) if str(tag_name_or_id).isdigit() else Tag.objects.get_or_create(name=str(tag_name_or_id).lower())[0]
        except Tag.DoesNotExist: return Response({'error': f'Tag with ID "{tag_name_or_id}" not found.'}, status=status.HTTP_404_NOT_FOUND)
        page.tags.add(tag); return Response(PageSerializer(page, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['delete'], url_path='tags/(?P<tag_identifier>[^/.]+)', permission_classes=[permissions.IsAuthenticated])
    def manage_tags_remove(self, request, pk=None, tag_identifier=None):
        page = self.get_object()
        try: tag = Tag.objects.get(pk=tag_identifier) if str(tag_identifier).isdigit() else Tag.objects.get(name=str(tag_identifier).lower())
        except Tag.DoesNotExist: return Response({'error': f'Tag "{tag_identifier}" not found.'}, status=status.HTTP_404_NOT_FOUND)
        if not page.tags.filter(pk=tag.pk).exists(): return Response({'error': f'Tag "{tag_identifier}" is not on page.'}, status=status.HTTP_400_BAD_REQUEST)
        page.tags.remove(tag); return Response(PageSerializer(page, context={'request': request}).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='revert/(?P<version_number_str>[0-9]+)', permission_classes=[permissions.IsAuthenticated])
    def revert(self, request, pk=None, version_number_str=None):
        page = self.get_object()
        try:
            version_number_to_revert_to = int(version_number_str)
            target_version = PageVersion.objects.get(page=page, version_number=version_number_to_revert_to)
        except PageVersion.DoesNotExist: return Response({'error': f'Version {version_number_str} not found.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError: return Response({'error': 'Invalid version number.'}, status=status.HTTP_400_BAD_REQUEST)

        if page.raw_content == target_version.raw_content and page.schema_version == target_version.schema_version:
             return Response({'message': 'Page content is already identical to this version.'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            page.raw_content = target_version.raw_content
            page.schema_version = target_version.schema_version
            new_current_version_number = page.version + 1
            page.version = new_current_version_number
            page.save()
            PageVersion.objects.create(
                page=page, version_number=new_current_version_number,
                raw_content=page.raw_content, schema_version=page.schema_version,
                author=request.user,
                commit_message=request.data.get('commit_message', f'Reverted to content of version {version_number_to_revert_to}.')
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
