from django.urls import path
from .views import PageDetailView # Import the new view

app_name = 'pages'

urlpatterns = [
    path('<slug:slug>/', PageDetailView.as_view(), name='page-detail'),
    # Example for a future list view:
    # path('', PageListView.as_view(), name='page-list'),
]
