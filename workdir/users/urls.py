from django.urls import path
from .views import UserListView, GroupListView

app_name = 'users'

urlpatterns = [
    path('users/', UserListView.as_view(), name='user-list'),
    path('groups/', GroupListView.as_view(), name='group-list'),
]
