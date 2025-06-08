from rest_framework import serializers
from .models import Page, Attachment, Tag, PageVersion # Ensure all models are imported
from workspaces.models import Workspace, Space

# --- Serializer for PageViewSet (CRUD operations) ---
class TagSerializer(serializers.ModelSerializer): # Re-added from original
    class Meta:
        model = Tag
        fields = ['id', 'name']

class PageSerializer(serializers.ModelSerializer): # This is for PageViewSet (CRUD)
    author_username = serializers.ReadOnlyField(source='author.username', allow_null=True)
    tags = TagSerializer(many=True, read_only=True) # Keep tags read-only for basic CRUD, managed by actions
    space_key = serializers.CharField(source='space.key', read_only=True, allow_null=True) # Display space key

    class Meta:
        model = Page
        fields = [
            'id', 'space', 'space_key', 'title', 'slug', 'content_json', 'schema_version',
            'parent', # Changed from parent_page to parent to match model
            'author', 'author_username',
            'version',
            'tags',
            # 'is_deleted', 'deleted_at', # These are handled by perform_destroy in ViewSet
            'original_confluence_id', 'imported_by',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'author', 'author_username', 'slug', # Slug is auto-generated
            'version',
            # 'is_deleted', 'deleted_at', # Not directly settable by client
            'created_at', 'updated_at',
            'tags', 'space_key', 'imported_by' # imported_by set by task
        ]
        extra_kwargs = {
            'content_json': {'required': True},
            'space': {'queryset': Space.objects.filter(is_deleted=False), 'required': True},
             # Parent is optional
            'parent': {'queryset': Page.objects.filter(is_deleted=False), 'required': False, 'allow_null': True},
        }

class PageVersionSerializer(serializers.ModelSerializer): # Re-added from original
    author_username = serializers.ReadOnlyField(source='author.username', allow_null=True)
    class Meta:
        model = PageVersion
        fields = ['id', 'page', 'version_number', 'content_json', 'schema_version', 'author', 'author_username', 'commit_message', 'created_at']


# --- Serializers for new PageDetailView (Read-only Detail) ---
class WorkspaceRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        if not value:
            return None
        return {'id': value.id, 'name': value.name}

class SpaceRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        if not value:
            return None
        return {'id': value.id, 'name': value.name, 'key': getattr(value, 'key', None)}

class ParentPageRelatedField(serializers.RelatedField):
    def to_representation(self, value):
        if not value:
            return None
        return {'id': value.id, 'title': value.title}

class AttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = ['id', 'original_filename', 'file_url', 'mime_type', 'created_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

class PageDetailSerializer(serializers.ModelSerializer):
    workspace = WorkspaceRelatedField(read_only=True, source='space.workspace')
    space = SpaceRelatedField(read_only=True)
    parent = ParentPageRelatedField(read_only=True, allow_null=True) # Allow null for top-level pages
    children = serializers.SerializerMethodField()
    page_specific_attachments = AttachmentSerializer(many=True, read_only=True)
    imported_by_username = serializers.CharField(source='imported_by.username', read_only=True, allow_null=True)
    author_username = serializers.CharField(source='author.username', read_only=True, allow_null=True) # Added author for detail view

    class Meta:
        model = Page
        fields = [
            'id', 'title', 'slug', 'content_json',
            'workspace', 'space', 'parent', 'children',
            'original_confluence_id',
            'author', 'author_username', # Added author for detail view
            'imported_by', 'imported_by_username',
            'version', 'schema_version', # Added version fields
            'created_at', 'updated_at',
            'page_specific_attachments'
        ]
        read_only_fields = fields # All fields are read-only for this detail serializer

    def get_children(self, obj):
        # Page model does not have is_deleted. If it did, filter here.
        return [{'id': child.id, 'title': child.title, 'slug': child.slug} for child in obj.children.all()]
