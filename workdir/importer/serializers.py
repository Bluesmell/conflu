from rest_framework import serializers
from .models import ConfluenceUpload
# Workspace and Space models are not directly used for defining serializer fields here,
# but their instances will be used by the view to populate the ConfluenceUpload instance.

class ConfluenceUploadSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    target_workspace_id = serializers.IntegerField(source='target_workspace.id', read_only=True, allow_null=True)
    target_workspace_name = serializers.CharField(source='target_workspace.name', read_only=True, allow_null=True)
    target_space_id = serializers.IntegerField(source='target_space.id', read_only=True, allow_null=True)
    target_space_name = serializers.CharField(source='target_space.name', read_only=True, allow_null=True)

    file_url = serializers.SerializerMethodField(read_only=True)
    progress_status_display = serializers.CharField(source='get_progress_status_display', read_only=True) # For human-readable status

    class Meta:
        model = ConfluenceUpload
        fields = [
            'id', 'file', 'file_url',
            'user',
            'user_username',
            'uploaded_at',
            'status', # Old status field
            'progress_status', # New granular status field
            'progress_status_display', # Display for progress_status
            'progress_percent',
            'task_id',
            'target_workspace',
            'target_workspace_id',
            'target_workspace_name',
            'target_space',
            'target_space_id',
            'target_space_name',
            # New progress tracking fields
            'pages_succeeded_count',
            'pages_failed_count',
            'attachments_succeeded_count',
            'progress_message',
            'error_details',
        ]

        read_only_fields = [
            'id',
            'user',
            'user_username',
            'uploaded_at',
            'status', # Old status
            'progress_status', # New granular status
            'progress_status_display',
            'progress_percent',
            'task_id',
            'target_workspace_id',
            'target_workspace_name',
            'target_space_id',
            'target_space_name',
            'pages_succeeded_count',
            'pages_failed_count',
            'attachments_succeeded_count',
            'progress_message',
            'error_details',
            'file_url'
        ]

        extra_kwargs = {
            'file': {'required': True, 'write_only': True}, # file is primarily for upload, file_url for GET
            'target_workspace': {'read_only': True},
            'target_space': {'read_only': True}
        }

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            if request:
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url
        return None

from .models import FallbackMacro # Import FallbackMacro model

class FallbackMacroSerializer(serializers.ModelSerializer):
    page_version_id = serializers.IntegerField(source='page_version.id', read_only=True)
    page_title = serializers.CharField(source='page_version.page.title', read_only=True) # Optional: provide some context

    class Meta:
        model = FallbackMacro
        fields = [
            'id',
            'macro_name',
            'raw_macro_content',
            'import_notes',
            'placeholder_id_in_content', # This UUID might be useful for frontend to locate it if needed
            'page_version_id', # Context: which page version this macro belongs to
            'page_title',      # Context: title of the page this macro belongs to
        ]
        read_only_fields = fields # Typically, these details are read-only once created by importer
