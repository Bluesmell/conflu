from rest_framework import viewsets
from .models import Page, PageVersion, Tag
from .serializers import PageSerializer, PageVersionSerializer, TagSerializer

class PageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Page.objects.filter(is_deleted=False)
    serializer_class = PageSerializer

class PageVersionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PageVersion.objects.all()
    serializer_class = PageVersionSerializer

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
