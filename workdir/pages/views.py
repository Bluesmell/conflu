
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status, serializers # Ensure 'serializers' is imported here
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, inline_serializer # 'serializers' removed from here
from guardian.shortcuts import assign_perm
from .models import Page, PageVersion, Tag, Space
from .serializers import PageSerializer, PageVersionSerializer, TagSerializer
from core.permissions import DjangoObjectPermissionsOrAnonReadOnly

class PageViewSet(viewsets.ModelViewSet):
    queryset = Page.objects.filter(is_deleted=False).prefetch_related('tags').select_related('author', 'space')
    serializer_class = PageSerializer
    permission_classes = [DjangoObjectPermissionsOrAnonReadOnly]

    def perform_create(self, serializer):
        with transaction.atomic():
            page = serializer.save(author=self.request.user, version=1)
            user = self.request.user
            assign_perm('pages.view_page', user, page)
            assign_perm('pages.change_page', user, page)
            assign_perm('pages.delete_page', user, page)
            # print(f"Assigned view, change, delete permissions for page '{page.title}' to user '{user.username}'.")

            PageVersion.objects.create(
                page=page,
                version_number=1,
                raw_content=serializer.validated_data.get('raw_content', {}),
                schema_version=serializer.validated_data.get('schema_version', 1),
                author=user,
                commit_message="Initial version."
            )

    @extend_schema(
        request=PageSerializer,
        responses={200: PageSerializer},
        description="Updates a page and creates a new version. A 'commit_message' can be provided in the request body."
    )
    def perform_update(self, serializer):
        with transaction.atomic():
            page_instance = serializer.instance
            new_version_number = page_instance.version + 1

            updated_page = serializer.save(version=new_version_number)
            user = self.request.user

            commit_message = self.request.data.get('commit_message', f'Version {new_version_number}.')
            PageVersion.objects.create(
                page=updated_page,
                version_number=new_version_number,
                raw_content=updated_page.raw_content,
                schema_version=updated_page.schema_version,
                author=user,
                commit_message=commit_message
            )

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save()

    @extend_schema(
        request=inline_serializer(
            name='PageTagAddRequest',
            fields={'tag': serializers.CharField(help_text="Name or ID of the tag to add.")}
        ),
        responses={200: PageSerializer}
    )
    @action(detail=True, methods=['post'], url_path='tags', permission_classes=[DjangoObjectPermissionsOrAnonReadOnly])
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
        parameters=[OpenApiParameter(name="tag_pk_or_name", description="Key or name of tag to remove.", required=True, type=OpenApiTypes.STR, location=OpenApiParameter.PATH)],
        responses={200: PageSerializer}
    )
    @action(detail=True, methods=['delete'], url_path='tags/(?P<tag_pk_or_name>[^/.]+)', permission_classes=[DjangoObjectPermissionsOrAnonReadOnly])
    def remove_page_tag(self, request, pk=None, tag_pk_or_name=None):
        page = self.get_object()
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
            fields={'commit_message': serializers.CharField(required=False, help_text="Commit message for revert.")}
        ),
        parameters=[OpenApiParameter(name="version_number_str", description="Version to revert to.", required=True, type=OpenApiTypes.INT, location=OpenApiParameter.PATH)],
        responses={200: PageSerializer}
    )
    @action(detail=True, methods=['post'], url_path='revert/(?P<version_number_str>[0-9]+)', permission_classes=[DjangoObjectPermissionsOrAnonReadOnly])
    def revert(self, request, pk=None, version_number_str=None):
        page = self.get_object()
        try:
            version_number_to_revert_to = int(version_number_str)
            target_version = PageVersion.objects.get(page=page, version_number=version_number_to_revert_to)
        except PageVersion.DoesNotExist:
            return Response({'error': f'Version {version_number_str} not found for this page.'}, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({'error': 'Invalid version number format.'}, status=status.HTTP_400_BAD_REQUEST)

        if page.raw_content == target_version.raw_content and page.schema_version == target_version.schema_version:
             return Response({'message': 'Page content is already identical to this version.'}, status=status.HTTP_200_OK)

        with transaction.atomic():
            page.raw_content = target_version.raw_content
            page.schema_version = target_version.schema_version
            new_current_version_number = page.version + 1
            page.version = new_current_version_number
            page.updated_at = timezone.now()
            page.save()

            PageVersion.objects.create(
                page=page,
                version_number=new_current_version_number,
                raw_content=page.raw_content,
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
