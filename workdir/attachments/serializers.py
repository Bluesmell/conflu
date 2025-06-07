from rest_framework import serializers
from .models import Attachment
from pages.models import Page

class AttachmentSerializer(serializers.ModelSerializer):
    uploader_username = serializers.ReadOnlyField(source='uploader.username')
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Attachment
        fields = [
            'id', 'page', 'uploader', 'uploader_username',
            'file_name', 'file', 'file_url', 'mime_type', 'size_bytes',
            'scan_status', 'scanned_at', 'created_at'
        ]
        read_only_fields = [
            'uploader', 'uploader_username',
            'mime_type', 'size_bytes',
            'scan_status', 'scanned_at',
            'created_at',
            'file_url'
        ]
        extra_kwargs = {
            'file': {'write_only': True, 'required': True},
            'page': {'queryset': Page.objects.filter(is_deleted=False)},
            'file_name': {'required': True}
        }

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url') and request:
            return request.build_absolute_uri(obj.file.url)
        return None

    def create(self, validated_data):
        uploaded_file = validated_data.get('file')
        if uploaded_file:
            validated_data['mime_type'] = uploaded_file.content_type if uploaded_file.content_type else 'application/octet-stream'
            validated_data['size_bytes'] = uploaded_file.size
        return super().create(validated_data)
