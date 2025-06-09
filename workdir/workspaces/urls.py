from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SpaceViewSet,
    ListSpacePermissionsView,
    AssignUserSpacePermissionView,
    AssignGroupSpacePermissionView,
    RemoveUserSpacePermissionsView,
    RemoveGroupSpacePermissionsView
)

app_name = 'workspaces'

router = DefaultRouter()
router.register(r'spaces', SpaceViewSet, basename='space')

urlpatterns = [
    # Routes for SpaceViewSet (e.g., /api/v1/workspaces/spaces/, /api/v1/workspaces/spaces/{space_key}/)
    path('', include(router.urls)),

    # Routes for Space Permissions Management
    path('spaces/<str:space_key>/permissions/', ListSpacePermissionsView.as_view(), name='space-list-permissions'),
    path('spaces/<str:space_key>/permissions/user/', AssignUserSpacePermissionView.as_view(), name='space-assign-user-permission'),
    path('spaces/<str:space_key>/permissions/group/', AssignGroupSpacePermissionView.as_view(), name='space-assign-group-permission'),
    path('spaces/<str:space_key>/permissions/user/<int:user_id>/', RemoveUserSpacePermissionsView.as_view(), name='space-remove-user-permission'),
    path('spaces/<str:space_key>/permissions/group/<int:group_id>/', RemoveGroupSpacePermissionsView.as_view(), name='space-remove-group-permission'),
]
