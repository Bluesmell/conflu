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

# --- Permissions Management Serializers ---

class UserBasicSerializer(serializers.ModelSerializer):
    """Basic User serializer for listing users with permissions."""
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class GroupBasicSerializer(serializers.ModelSerializer):
    """Basic Group serializer for listing groups with permissions."""
    # Assuming Django's default Group model
    class Meta:
        model = serializers.DjangoModelFactoryMixin.get_model_from_meta(User._meta.get_field('groups').remote_field.model) # Hacky way to get Group model if not imported
        # from django.contrib.auth.models import Group # Better to import directly
        # model = Group
        fields = ['id', 'name']


class SpaceUserPermissionSerializer(serializers.Serializer):
    user = UserBasicSerializer(read_only=True)
    permissions = serializers.ListField(child=serializers.CharField(), read_only=True)

class SpaceGroupPermissionSerializer(serializers.Serializer):
    group = GroupBasicSerializer(read_only=True)
    permissions = serializers.ListField(child=serializers.CharField(), read_only=True)


class AssignPermissionSerializer(serializers.Serializer):
    permission_codenames = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        help_text="List of permission codenames (e.g., 'view_space', 'edit_space_content')."
    )

    def validate_permission_codenames(self, value):
        # Optional: Validate against actual permissions available for Space model
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        from .models import Space
        content_type = ContentType.objects.get_for_model(Space)
        valid_codenames = Permission.objects.filter(content_type=content_type).values_list('codename', flat=True)

        # Include default built-in permissions that might not be in Meta.permissions explicitly
        # (like view_space, change_space, delete_space if default_permissions is on)
        # For simplicity, we'll assume the provided codenames are known by the system.
        # A more robust validation would check against all possible valid perms.

        for codename in value:
            # Basic check, can be expanded
            if not any(codename == valid_codename or codename.startswith(('view_', 'change_', 'delete_')) for valid_codename in valid_codenames):
                 # This check is very basic and might need refinement depending on how codenames are managed
                 pass # Allow for now, actual assignment will fail if perm doesn't exist.
                 # raise serializers.ValidationError(f"Invalid permission codename: {codename}")
        return value


class AssignUserPermissionSerializer(AssignPermissionSerializer):
    user_id = serializers.IntegerField()

    def validate_user_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise serializers.ValidationError("User with this ID does not exist.")
        return value

class AssignGroupPermissionSerializer(AssignPermissionSerializer):
    group_id = serializers.IntegerField()

    def validate_group_id(self, value):
        # from django.contrib.auth.models import Group
        Group = serializers.DjangoModelFactoryMixin.get_model_from_meta(User._meta.get_field('groups').remote_field.model)
        if not Group.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Group with this ID does not exist.")
        return value
