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

# New imports for PageDetailView & PageSearchView
from rest_framework.generics import RetrieveAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly

# For Search
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank, SearchHeadline
from django.db.models import F, Q
from django.contrib.postgres.search import TrigramSimilarity # For fuzzy matching
from .serializers import PageSearchSerializer # Import the new search serializer


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


# --- New PageSearchView ---
class PageSearchView(ListAPIView):
    """
    API view for searching pages.
    Accepts a query parameter 'q'.
    Optionally accepts 'space_key' to filter by space.
    """
    serializer_class = PageSearchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] # Or IsAuthenticated if search is not public

    def get_queryset(self):
        query_string = self.request.query_params.get('q', '').strip()
        space_key = self.request.query_params.get('space_key', None)

        if not query_string:
            return Page.objects.none() # No query, no results

        # Basic SearchVector configuration (title and content)
        # This assumes 'search_vector' field is already populated on the Page model
        # and is a SearchVectorField('title', 'content_text_field_name')

        search_query = SearchQuery(query_string, search_type='websearch') # 'websearch' is good for multiple terms

        queryset = Page.objects.filter(is_deleted=False) # Exclude deleted pages

        if space_key:
            queryset = queryset.filter(space__key=space_key)

        # Full-text search using the precomputed search_vector
        # Annotate with rank and headline
        # Note: SearchHeadline requires the field names used in the SearchVector definition on the model.
        # If search_vector = SearchVector('title', 'content_json_text'), then use those here.
        # Assuming title and a text version of content_json were used.
        # For simplicity, we'll use 'title' and the helper function for content_json if direct field not available.
        # However, SearchHeadline works best if the fields are directly queryable.
        # Given our model, we search on 'search_vector' and headline on 'title' and a text version of 'content_json'.
        # The `prosemirror_json_to_text` helper is in models.py, not directly usable in query annotations
        # without more complex setup like custom database functions or pre-saving text content.
        # For headline, we'll use title for now. A more advanced headline would involve content.

        queryset = queryset.annotate(
            rank=SearchRank(F('search_vector'), search_query),
            # Basic headline on title. For content, it's more complex without a dedicated text field.
            headline=SearchHeadline(
                'title',  # Field to generate headline from
                search_query,
                start_sel='<mark>',
                stop_sel='</mark>',
                max_words=50,
                min_words=25,
                max_fragments=3,
            )
            # TODO: Add headline for content if a plain text version of content_json is stored or accessible
            # For example, if you add a 'plain_content' field to Page model updated by signal:
            # headline_content=SearchHeadline('plain_content', search_query, ...)
            # Then combine headlines or choose one.
        ).filter(search_vector=search_query).order_by('-rank', 'title')

        # Optional: Add TrigramSimilarity for fuzzy matching if FTS results are too few or query is short
        # This is a secondary filter or could be a fallback.
        # For example:
        # if not queryset.exists() and len(query_string) > 3: # Arbitrary length check
        #     similar_pages = Page.objects.annotate(
        #         similarity=TrigramSimilarity('title', query_string) + TrigramSimilarity(Cast('content_json', TextField()), query_string) / 2 # Rough example
        #     ).filter(similarity__gt=0.2).order_by('-similarity') # Adjust threshold
        #     return similar_pages
        # This is a simplified example; integrating trigram well often means combining results or using it conditionally.

        return queryset

    @extend_schema(
        parameters=[
            OpenApiParameter(name='q', description='Search query term.', required=True, type=OpenApiTypes.STR),
            OpenApiParameter(name='space_key', description='Optional: Key of the space to filter search results by.', required=False, type=OpenApiTypes.STR),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
