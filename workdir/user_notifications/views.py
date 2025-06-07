
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Notification, Activity
from .serializers import NotificationSerializer, ActivitySerializer

class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Notifications.
    Allows listing notifications for the authenticated user and marking them as read.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Users should only see their own notifications
        return Notification.objects.filter(recipient=self.request.user).select_related(
            'recipient', 'actor_content_type', 'content_type' # Optimize GFK lookups if possible, though actor/target still separate
        )

    # Prevent creating notifications directly via this API for now
    # Notifications should be created by the system in response to events.
    # Allow update for marking as read (though bulk action is better)
    # Allow destroy for user to delete notification.
    http_method_names = ['get', 'put', 'patch', 'delete', 'head', 'options']


    @action(detail=False, methods=['post'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request):
        """
        Marks all unread notifications for the current user as read.
        """
        updated_count = Notification.objects.filter(recipient=request.user, read=False).update(read=True)
        return Response({'status': 'all notifications marked as read', 'updated_count': updated_count})

    @action(detail=True, methods=['post'], url_path='mark-as-read')
    def mark_as_read(self, request, pk=None):
        """
        Marks a specific notification as read.
        """
        notification = self.get_object()
        if notification.recipient != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN) # Should be caught by get_queryset anyway

        if not notification.read:
            notification.read = True
            notification.save(update_fields=['read'])
            return Response(NotificationSerializer(notification, context={'request': request}).data)
        return Response({'status': 'notification already marked as read'}, status=status.HTTP_200_OK)

    # Could add mark_as_unread as well if needed

class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing Activities.
    Activities are read-only and represent a log of actions in the system.
    """
    serializer_class = ActivitySerializer
    permission_classes = [permissions.IsAuthenticated] # Or IsAdminUser depending on who can see activity

    def get_queryset(self):
        # For now, let users see all activities. This might need refinement based on privacy/roles.
        # Or, filter by activities where the user is the actor or involved in target/context.
        # Example: return Activity.objects.filter(actor=self.request.user)
        return Activity.objects.all().select_related(
            'actor', 'target_content_type', 'context_content_type' # Optimize GFK lookups
        ).prefetch_related('target', 'context') # Prefetch actual generic objects
