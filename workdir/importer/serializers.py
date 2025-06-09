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

    class Meta:
        model = ConfluenceUpload
        fields = [
            'id', 'file', 'file_url',
            'user',
            'user_username',
            'uploaded_at', 'status', 'task_id',
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
            'error_details'
        ]

        read_only_fields = [
            'id',
            'user',
            'user_username',
            'uploaded_at',
            'status',
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
