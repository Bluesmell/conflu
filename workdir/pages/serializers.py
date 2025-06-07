from rest_framework import serializers
from .models import Page, PageVersion, Tag

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name']

class PageVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PageVersion
        fields = ['id', 'page', 'version_number', 'raw_content', 'schema_version', 'author', 'commit_message', 'created_at']

class PageSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    # versions = PageVersionSerializer(many=True, read_only=True) # Example if we want to nest versions

    class Meta:
        model = Page
        fields = [
            'id', 'space', 'title', 'raw_content', 'schema_version',
            'parent_page', 'author', 'version',
            'tags', 'created_at', 'updated_at'
            # 'versions',
        ]
