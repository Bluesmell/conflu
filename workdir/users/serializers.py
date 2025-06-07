from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirm password")

    class Meta:
        model = User
        fields = ('username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'email': {'required': True}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        return attrs

    def create(self, validated_data):
        user = User.objects.create_user( # Use create_user to handle username and email
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password']) # Hash password
        if validated_data.get('first_name'):
            user.first_name = validated_data.get('first_name')
        if validated_data.get('last_name'):
            user.last_name = validated_data.get('last_name')
        user.save()
        return user

class UserSimpleSerializer(serializers.ModelSerializer):
    """
    Basic serializer for User model to represent users in a simple, non-sensitive way.
    Used for actor, recipient, etc. fields in other serializers.
    """
    class Meta:
        model = User  # Assumes User is already imported from django.contrib.auth.models
        fields = ['id', 'username', 'first_name', 'last_name', 'email'] # Added email as it was in UserRegistrationSerializer fields
        read_only_fields = fields # Typically, simple serializers are read-only representations
