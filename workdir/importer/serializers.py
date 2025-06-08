from rest_framework import serializers
from .models import ConfluenceUpload
# Workspace and Space models are not directly used for defining serializer fields here,
# but their instances will be used by the view to populate the ConfluenceUpload instance.
# Source attribute like 'target_workspace.id' will work as long as the instance has it.

class ConfluenceUploadSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True, allow_null=True)

    # Display fields for target workspace and space for GET requests and POST responses
    target_workspace_id = serializers.IntegerField(source='target_workspace.id', read_only=True, allow_null=True)
    target_workspace_name = serializers.CharField(source='target_workspace.name', read_only=True, allow_null=True)
    target_space_id = serializers.IntegerField(source='target_space.id', read_only=True, allow_null=True)
    target_space_name = serializers.CharField(source='target_space.name', read_only=True, allow_null=True)

    class Meta:
        model = ConfluenceUpload
        fields = [
            'id', 'file',
            'user',  # This will be the user's ID (PK)
            'user_username',
            'uploaded_at', 'status', 'task_id',
            'target_workspace', # Actual FK field (shows ID in default DRF representation for FKs)
            'target_workspace_id', # Explicit ID from source for clarity / if FK is not in fields
            'target_workspace_name',
            'target_space', # Actual FK field
            'target_space_id',   # Explicit ID from source
            'target_space_name'
        ]

        # Fields that are not set directly by the client during POST create,
        # or are derived.
        read_only_fields = [
            'id',
            'user', # Set by the view based on request.user
            'user_username',
            'uploaded_at',
            'status',
            'task_id',
            'target_workspace_id', # Display field, read-only
            'target_workspace_name', # Display field, read-only
            'target_space_id',   # Display field, read-only
            'target_space_name'  # Display field, read-only
        ]

        # 'file' is the primary input field for POST.
        # 'target_workspace' and 'target_space' (model FKs) are also treated as effectively read-only
        # in terms of direct data binding from the POST payload that this serializer handles by default.
        # The view will extract separate IDs, validate them, and pass instances to serializer.save().
        # To make them appear in GET responses by default, they are included in 'fields'.
        # To prevent them from being writable via this serializer directly from POST data (expecting IDs instead):
        extra_kwargs = {
            'file': {'required': True}, # 'write_only': False is default if not in read_only_fields
            'target_workspace': {'read_only': True}, # Will be set by view logic
            'target_space': {'read_only': True}      # Will be set by view logic
        }
