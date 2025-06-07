from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from rest_framework import viewsets, permissions, parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from guardian.shortcuts import assign_perm
from .models import Attachment
from .serializers import AttachmentSerializer
from .tasks import scan_attachment_file
from core.permissions import ExtendedDjangoObjectPermissionsOrAnonReadOnly # Using Extended
from django.utils.encoding import iri_to_uri

class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Attachments.
    Provides CRUD operations for attachments, including file uploads and secure downloads.
    Object-level permissions (e.g., 'attachments.view_attachment',
    'attachments.change_attachment', 'attachments.delete_attachment') are enforced
    using django-guardian. These are typically assigned to the uploader upon creation.
    The 'download' action also respects these permissions.
    Read access for list/retrieve is controlled by the permission class;
    by default, it requires 'view_attachment' object permission for specific instances.
    Triggers an asynchronous virus scan for new uploads.
    """
    queryset = Attachment.objects.all().select_related('page', 'uploader')
    serializer_class = AttachmentSerializer
    permission_classes = [ExtendedDjangoObjectPermissionsOrAnonReadOnly] # Using Extended
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['page']

    def perform_create(self, serializer):
        """
        Sets the uploader to the current user, initial scan_status to 'pending',
        assigns object permissions to the uploader,
        and triggers the asynchronous virus scan task.
        Requires 'attachments.add_attachment' model-level permission.
        """
        uploader_user = None
        if self.request.user.is_authenticated:
            uploader_user = self.request.user

        attachment = serializer.save(uploader=uploader_user, scan_status='pending')

        if uploader_user:
            assign_perm('attachments.view_attachment', uploader_user, attachment)
            assign_perm('attachments.change_attachment', uploader_user, attachment)
            assign_perm('attachments.delete_attachment', uploader_user, attachment)
            # print(f"Assigned CRUD permissions for attachment {attachment.pk} to user {uploader_user.username}.")

        scan_attachment_file.delay(attachment.pk) # Direct call
        # print(f"Attachment {attachment.pk} created. Scan task trigger dispatched.")


    @action(detail=True, methods=['get'], url_path='download', permission_classes=[ExtendedDjangoObjectPermissionsOrAnonReadOnly]) # Using Extended
    def download(self, request, pk=None):
        """
        Provides a secure download link for the attachment file.
        Requires 'attachments.view_attachment' object-level permission.
        Implements Zero-Trust Attachment Download headers.
        Blocks download if scan_status is 'infected', 'pending', or 'error'.
        """
        attachment = self.get_object()

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
            encoded_filename = iri_to_uri(attachment.file_name)
            response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
            response['X-Content-Type-Options'] = 'nosniff'

            return response
        except FileNotFoundError:
            raise Http404("File not found.")
        except Exception as e:
            # print(f"Error serving file: {e}")
            return Response({"detail": "Error serving file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
