from rest_framework import viewsets
from .models import Space
from .serializers import SpaceSerializer
class SpaceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Space.objects.filter(is_deleted=False)
    serializer_class = SpaceSerializer
    lookup_field = 'key'
