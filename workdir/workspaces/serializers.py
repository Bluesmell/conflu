from rest_framework import serializers
from .models import Space
from django.contrib.auth import get_user_model

User = get_user_model()

class SpaceSerializer(serializers.ModelSerializer):
    # owner = serializers.PrimaryKeyRelatedField(read_only=True) # Alternative if only showing ID
    owner_username = serializers.ReadOnlyField(source='owner.username')

    class Meta:
        model = Space
        fields = [
            'id', 'key', 'name', 'description',
            'owner',        # Keep for writing during serializer.save(owner=...) in view
            'owner_username',
            'is_deleted', 'deleted_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            # 'owner' is effectively read-only from client's input perspective because
            # it's set in perform_create. If we include 'owner' in fields but not here,
            # it would expect client to provide it, which is not what we want for perform_create.
            # To make it truly settable only by perform_create and not by direct client POST/PUT,
            # it should be in read_only_fields.
            'owner',
            'owner_username',
            'is_deleted', 'deleted_at',
            'created_at', 'updated_at',
        ]
        # Key is typically immutable. Forcing it on create:
        # extra_kwargs = {
        #     'key': {'validators': [UniqueValidator(queryset=Space.objects.all())]} # Handled by model's unique=True
        # }

    # Add custom validation for 'key' if needed, e.g., to prevent update after creation
    # def update(self, instance, validated_data):
    #     validated_data.pop('key', None) # Disallow 'key' updates
    #     return super().update(instance, validated_data)
