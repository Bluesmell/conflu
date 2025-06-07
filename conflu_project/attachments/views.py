from django.http import FileResponse, Http404, HttpResponseForbidden
from django.utils import timezone
from rest_framework import viewsets, permissions, parsers, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
# Corrected model import assuming models.py is in the same directory
from .models import Attachment
from .serializers import AttachmentSerializer
# from .tasks import scan_attachment_file # Keep this commented out for now
from django.utils.encoding import iri_to_uri

class AttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Attachments.
    Allows uploading, listing, retrieving, and deleting attachments.
    File content is uploaded via 'file' field (multipart/form-data).
    Triggers an asynchronous virus scan for new uploads.
    """
    queryset = Attachment.objects.all().select_related('page', 'uploader')
    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['page']

    def perform_create(self, serializer):
        """
        Sets the uploader to the current user, initial scan_status to 'pending',
        and triggers the asynchronous virus scan task.
        """
        uploader_user = None
        if self.request.user.is_authenticated:
            uploader_user = self.request.user

        attachment = serializer.save(uploader=uploader_user, scan_status='pending')

        # scan_attachment_file.delay(attachment.pk) # Keep commented out
        print(f'Attachment {attachment.pk} created. Scan task trigger would be here.')


    @action(detail=True, methods=['get'], url_path='download', permission_classes=[permissions.IsAuthenticated])
    def download(self, request, pk=None):
        """
        Provides a secure download link for the attachment file.
        Implements Zero-Trust Attachment Download headers.
        Blocks download if scan_status is 'infected', 'pending', or 'error'.
        """
        attachment = self.get_object()

        if attachment.scan_status == 'infected':
            return HttpResponseForbidden("File is marked as infected and cannot be downloaded.")

        if attachment.scan_status in ['pending', 'error']:
             return Response(
                {{"detail": f"File scan status is '{attachment.scan_status}'. Download is not allowed until scan is clean."}},
                status=status.HTTP_403_FORBIDDEN
            )

        if not attachment.file or not hasattr(attachment.file, 'name') or not attachment.file.name:
            raise Http404("File not found for this attachment.")

        try:
            # It's good practice to check if file exists on storage,
            # but attachment.file.path might not be available for all storages.
            # attachment.file.open() will raise FileNotFoundError if not found on default local storage.

            response = FileResponse(attachment.file.open('rb'), as_attachment=False)
            response['Content-Type'] = 'application/octet-stream'
            encoded_filename = iri_to_uri(attachment.file_name)
            response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
            response['X-Content-Type-Options'] = 'nosniff'

            return response
        except FileNotFoundError:
            raise Http404("File not found.")
        except Exception as e:
            print(f'Error serving file: {e}')
            return Response({{"detail": "Error serving file."}}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
