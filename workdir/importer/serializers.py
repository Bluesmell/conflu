from rest_framework import serializers
from .models import ConfluenceUpload

class ConfluenceUploadSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ConfluenceUpload
        fields = [
            'id',
            'file',
            'user',
            'user_username',
            'uploaded_at',
            'status',
            'task_id'
        ]
        read_only_fields = ['id', 'user', 'user_username', 'uploaded_at', 'status', 'task_id']
