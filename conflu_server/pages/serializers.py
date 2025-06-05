from rest_framework import serializers
from .models import Space, Page # Assuming Space model is in pages.models

class SpaceSerializer(serializers.ModelSerializer):
    owner_username = serializers.ReadOnlyField(source='owner.username') # To display username
    # pages_count = serializers.SerializerMethodField() # Example for later

    class Meta:
        model = Space
        fields = ('id', 'key', 'name', 'description', 'owner', 'owner_username',
                  'is_deleted', 'deleted_at', 'created_at', 'updated_at')
        read_only_fields = ('owner', 'is_deleted', 'deleted_at') # Owner will be set automatically

    # def get_pages_count(self, obj):
    #     return obj.pages.count()

class PageSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')
    space_key = serializers.ReadOnlyField(source='space.key')
    # Ensure space is writeable by its ID, but space_key is read-only.
    space = serializers.PrimaryKeyRelatedField(queryset=Space.objects.all())


    class Meta:
        model = Page
        fields = (
            'id', 'space', 'space_key', 'title', 'raw_content', 'schema_version',
            'parent_page', 'author', 'author_username', 'version',
            'is_deleted', 'deleted_at', 'created_at', 'updated_at'
        )
        read_only_fields = ('author', 'version', 'is_deleted', 'deleted_at', 'space_key')
        # raw_content can be large, consider excluding from list views if performance becomes an issue
        # extra_kwargs = {
        #     'raw_content': {'write_only': True} # Example for making it write-only for create/update
        # }

# Basic Serializer for PageVersion - might be expanded later
class PageVersionSerializer(serializers.ModelSerializer):
    author_username = serializers.ReadOnlyField(source='author.username')

    class Meta:
        model = Page # This should be PageVersion, correcting based on task context.
        # Correcting to PageVersion
        from .models import PageVersion as ActualPageVersion
        model = ActualPageVersion
        fields = ('id', 'page', 'version_number', 'raw_content', 'schema_version',
                  'author', 'author_username', 'commit_message', 'created_at')
        read_only_fields = ('author', 'created_at')
