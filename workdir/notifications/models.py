from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Notification(models.Model):
    \"\"\"
    Represents a notification for a user.
    Can be linked to a specific object (e.g., a page, a comment) using GenericForeignKey.
    \"\"\"
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    verb = models.CharField(max_length=255)  # e.g., "commented on", "mentioned you in", "shared"
    message = models.TextField(blank=True)   # Optional detailed message

    # Generic relation to an object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('content_type', 'object_id') # The object the notification is about

    # Generic relation to an actor (the user who triggered the notification)
    actor_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='actor_notifications')
    actor_object_id = models.PositiveIntegerField(null=True, blank=True)
    actor = GenericForeignKey('actor_content_type', 'actor_object_id')

    timestamp = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    emailed = models.BooleanField(default=False) # If a notification email has been sent

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['recipient', 'read']),
        ]

    def __str__(self):
        if self.target:
            return f'{self.actor} {self.verb} {self.target} for {self.recipient.username}'
        return f'{self.actor} {self.verb} for {self.recipient.username}' # Fallback if no direct target

class Activity(models.Model):
    \"\"\"
    Represents an action performed by a user within the system (activity stream).
    Similar to Notification but for logging actions rather than direct user alerts.
    \"\"\"
    # User who performed the action
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activities')
    verb = models.CharField(max_length=255)  # e.g., "created_page", "uploaded_attachment", "edited_profile"

    # Optional: The direct object of the action (e.g., the page that was created)
    target_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='target_activities')
    target_object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('target_content_type', 'target_object_id')

    # Optional: The context of the action (e.g., the workspace where a page was created)
    context_content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True, related_name='context_activities')
    context_object_id = models.PositiveIntegerField(null=True, blank=True)
    context = GenericForeignKey('context_content_type', 'context_object_id')

    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    extra_data = models.JSONField(null=True, blank=True) # For any other relevant information

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = "Activities" # Correct pluralization in Django admin

    def __str__(self):
        parts = [str(self.actor), self.verb]
        if self.target:
            parts.append(str(self.target))
        if self.context:
            parts.extend(["in", str(self.context)])
        return " ".join(parts)

EOF && echo "--- Content of notifications/models.py ---" && cat notifications/models.py && echo "--- Running Django project check (after creating notifications app and models) ---" && python manage.py check
