from rest_framework import serializers
from .models import Space
class SpaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Space
        fields = ['id', 'key', 'name', 'description', 'owner', 'created_at', 'updated_at']
