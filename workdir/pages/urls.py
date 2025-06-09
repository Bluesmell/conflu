from django.urls import path, include # Added include
from rest_framework.routers import DefaultRouter
from .views import PageDetailView, PageViewSet, PageSearchView # Added PageViewSet and PageSearchView

app_name = 'pages'

# Router for PageViewSet
router = DefaultRouter()
router.register(r'pages', PageViewSet, basename='page') #  'pages' is the base endpoint for the ViewSet

urlpatterns = [
    # Existing path for PageDetailView (if you want to keep it separate, or it can be handled by ViewSet)
    # path('<slug:slug>/', PageDetailView.as_view(), name='page-detail-slug'), # Renamed to avoid clash if ViewSet uses slug for detail

    # URL for the search view
    path('search/pages/', PageSearchView.as_view(), name='page-search'),

    # Include ViewSet routes. This will generate routes like /api/v1/pages/, /api/v1/pages/{id}/, etc.
    # Make sure this is distinct from any direct paths like the PageDetailView if it's kept.
    # If PageViewSet's detail route uses slug, it might conflict with the PageDetailView path above.
    # For now, assume PageViewSet uses PK for its detail routes, or adjust lookup_field.
    path('', include(router.urls)), # This includes all PageViewSet routes
]

# Note: The original PageDetailView path was '<slug:slug>/'.
# If PageViewSet is also configured to use 'slug' for its detail view,
# ensure the order or path structure prevents clashes.
# For example, prefix ViewSet routes: path('crud/', include(router.urls))
# Or ensure PageDetailView's path is more specific if it's kept separate from ViewSet.
# Given PageViewSet is comprehensive, PageDetailView might become redundant unless it serves a very specific purpose
# not covered by the ViewSet's retrieve action with PageDetailSerializer.
# For now, I'm commenting out the original PageDetailView path to avoid potential immediate conflicts
# with the ViewSet's default routing. The ViewSet can handle detail views.
# If PageDetailView with slug is critical and separate, its path needs to be distinct.
# For example: path('display/<slug:slug>/', PageDetailView.as_view(), name='page-detail-slug'),
