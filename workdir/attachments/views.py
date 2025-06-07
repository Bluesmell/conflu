
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from rest_framework import viewsets, permissions, parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import assign_perm # For assigning permissions
from .models import Attachment
from .serializers import AttachmentSerializer
from .tasks import scan_attachment_file
from core.permissions import DjangoObjectPermissionsOrAnonReadOnly # Corrected Import shared permission class
# import os as os_path # Alias os to avoid conflict - not needed here, os is already imported by this script
from django.utils.encoding import iri_to_uri

class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Attachments.
    Allows uploading, listing, retrieving, and deleting attachments.
    File content is uploaded via 'file' field (multipart/form-data).
    Triggers an asynchronous virus scan for new uploads.
    Object-level permissions are enforced using django-guardian.
    """
    queryset = Attachment.objects.all().select_related('page', 'uploader')
    serializer_class = AttachmentSerializer
    permission_classes = [DjangoObjectPermissionsOrAnonReadOnly] # Use shared class
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['page']

    def perform_create(self, serializer):
        """
        Sets the uploader to the current user, initial scan_status to 'pending',
        assigns object permissions to the uploader,
        and triggers the asynchronous virus scan task.
        """
        uploader_user = None
        if self.request.user.is_authenticated:
            uploader_user = self.request.user
        else:
            # This case should ideally be prevented by permission_classes on ViewSet create action
            # For now, if it happens, attachment will have no specific uploader-owner.
            # Or, raise PermissionDenied if anonymous uploads are not desired.
            # DjangoObjectPermissionsOrAnonReadOnly allows POST if model has 'add' perm for user.
            # Let's assume IsAuthenticated will be eventually enforced for create.
            pass # Or handle error if anonymous upload isn't allowed


        attachment = serializer.save(uploader=uploader_user, scan_status='pending')

        if uploader_user: # Assign permissions only if there's an uploader
            assign_perm('attachments.view_attachment', uploader_user, attachment)
            assign_perm('attachments.change_attachment', uploader_user, attachment)
            assign_perm('attachments.delete_attachment', uploader_user, attachment)
            # print(f"Assigned view, change, delete permissions for attachment {attachment.pk} to user {uploader_user.username}.") # Silenced print

        scan_attachment_file.delay(attachment.pk)
        # print(f"Attachment {attachment.pk} created. Scan task trigger dispatched.") # Silenced print


    # Update and Destroy actions will now be subject to DjangoObjectPermissionsOrAnonReadOnly
    # (i.e. user needs 'change_attachment' or 'delete_attachment' on the object)

    @action(detail=True, methods=['get'], url_path='download', permission_classes=[DjangoObjectPermissionsOrAnonReadOnly])
    def download(self, request, pk=None):
        """
        Provides a secure download link for the attachment file.
        Requires 'view_attachment' permission on the object.
        Implements Zero-Trust Attachment Download headers.
        Blocks download if scan_status is 'infected', 'pending', or 'error'.
        """
        attachment = self.get_object() # Guardian's has_object_permission is checked here

        if attachment.scan_status == 'infected':
            return HttpResponseForbidden("File is marked as infected and cannot be downloaded.")

        if attachment.scan_status in ['pending', 'error']:
             return Response(
                {"detail": f"File scan status is '{attachment.scan_status}'. Download is not allowed until scan is clean."},
                status=status.HTTP_403_FORBIDDEN
            )

        if not attachment.file or not hasattr(attachment.file, 'name') or not attachment.file.name:
            raise Http404("File not found for this attachment.")

        try:
            if not attachment.file.storage.exists(attachment.file.name):
                raise Http404("File not found on storage.")

            response = FileResponse(attachment.file.open('rb'), as_attachment=False)
            response['Content-Type'] = 'application/octet-stream'
            encoded_filename = iri_to_uri(attachment.file_name) # Ensure iri_to_uri is imported
            response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
            response['X-Content-Type-Options'] = 'nosniff'

            return response
        except FileNotFoundError:
            raise Http404("File not found.")
        except Exception as e:
            # print(f"Error serving file: {e}") # Proper logging should be used
            return Response({"detail": "Error serving file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
