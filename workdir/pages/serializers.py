from rest_framework import serializers
from .models import Page, PageVersion, Tag
from workspaces.models import Space

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class PageSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    tags = TagSerializer(many=True, read_only=True)
    # space = serializers.PrimaryKeyRelatedField(queryset=Space.objects.filter(is_deleted=False)) # Alternative declaration

    class Meta:
        model = Page
        fields = [
            'id', 'space', 'title', 'raw_content', 'schema_version',
            'parent_page',
            'author', 'author_username',
            'version',
            'tags',
            'is_deleted', 'deleted_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [ # 'space' removed from here
            'author', 'author_username',
            'version',
            'is_deleted', 'deleted_at',
            'created_at', 'updated_at',
            'tags'
        ]
        extra_kwargs = {
            'raw_content': {'required': True},
            # 'space' is PrimaryKeyRelatedField, queryset is good for validation. Required by default.
            'space': {'queryset': Space.objects.filter(is_deleted=False)}
        }

class PageVersionSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    class Meta:
        model = PageVersion
        fields = ['id', 'page', 'version_number', 'raw_content', 'schema_version', 'author', 'author_username', 'commit_message', 'created_at']
