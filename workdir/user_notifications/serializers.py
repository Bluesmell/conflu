
from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import Notification, Activity
from users.serializers import UserSimpleSerializer # Assuming a simple user serializer exists

# GenericRelatedField alternative for more control if needed, or for dynamic serialization
# For now, we'll serialize actor/target/context by fetching them based on content_type and object_id
# or by using their string representation.

class GenericObjectRelatedField(serializers.RelatedField):
    """
    A custom field to serialize generic foreign keys.
    It tries to use a dedicated serializer if available, otherwise uses string representation.
    """
    def to_representation(self, value):
        if hasattr(value, 'get_serializer_class'): # Check for a hypothetical method on models
            SerializerClass = value.get_serializer_class()
            return SerializerClass(value, context=self.context).data
        if hasattr(value, 'name'): # e.g. Page model might have a 'name' or 'title'
            return str(value.name)
        if hasattr(value, 'title'):
            return str(value.title)
        return str(value)


class NotificationSerializer(serializers.ModelSerializer):
    recipient = UserSimpleSerializer(read_only=True) # Or just recipient_id = serializers.IntegerField()
    actor_detail = serializers.SerializerMethodField()
    target_detail = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ['id', 'recipient', 'verb', 'message', 'actor_detail', 'target_detail',
                  'timestamp', 'read', 'emailed',
                  'content_type', 'object_id', 'actor_content_type', 'actor_object_id'] # raw generic fk fields
        read_only_fields = ['timestamp', 'emailed', 'verb', 'message',
                            'actor_detail', 'target_detail',
                            'content_type', 'object_id', 'actor_content_type', 'actor_object_id']
                            # Recipient is set implicitly, read status updated via action

    def get_actor_detail(self, obj):
        if obj.actor:
            # Basic representation; could be expanded with specific serializers per actor type
            return {'type': obj.actor_content_type.model, 'id': obj.actor_object_id, 'str': str(obj.actor)}
        return None

    def get_target_detail(self, obj):
        if obj.target:
            # Basic representation; could be expanded
            return {'type': obj.content_type.model, 'id': obj.object_id, 'str': str(obj.target)}
        return None


class ActivitySerializer(serializers.ModelSerializer):
    actor = UserSimpleSerializer(read_only=True) # Or just actor_id
    target_detail = serializers.SerializerMethodField()
    context_detail = serializers.SerializerMethodField()

    class Meta:
        model = Activity
        fields = ['id', 'actor', 'verb', 'target_detail', 'context_detail',
                  'timestamp', 'ip_address', 'extra_data',
                  'target_content_type', 'target_object_id',
                  'context_content_type', 'context_object_id'] # raw generic fk fields
        read_only_fields = fields # Activities are typically read-only via API

    def get_target_detail(self, obj):
        if obj.target:
            return {'type': obj.target_content_type.model, 'id': obj.target_object_id, 'str': str(obj.target)}
        return None

    def get_context_detail(self, obj):
        if obj.context:
            return {'type': obj.context_content_type.model, 'id': obj.context_object_id, 'str': str(obj.context)}
        return None
