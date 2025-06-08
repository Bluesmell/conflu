
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import ConfluenceUpload # Updated import
from .serializers import ConfluenceUploadSerializer # New import
from .tasks import import_confluence_space

class ConfluenceImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        serializer = ConfluenceUploadSerializer(data=request.data)

        if serializer.is_valid():
            # Save the user associated with the upload
            confluence_upload = serializer.save(user=request.user)

            print(f"ConfluenceImportView: File uploaded. Record ID: {confluence_upload.id}, User: {request.user.username if request.user else 'Unknown'}")

            try:
                # Call Celery task with the ID of the ConfluenceUpload record
                import_confluence_space.delay(confluence_upload_id=confluence_upload.id)

                # Serialize the created object to return in the response
                response_data_serializer = ConfluenceUploadSerializer(confluence_upload)

                return Response({
                    "message": f"Confluence space import initiated for upload ID: {confluence_upload.id}.",
                    "data": response_data_serializer.data
                }, status=status.HTTP_202_ACCEPTED)
            except Exception as e:
                # If task dispatch fails, mark the upload as FAILED
                confluence_upload.status = ConfluenceUpload.STATUS_FAILED
                confluence_upload.save()
                print(f"ConfluenceImportView: Critical error dispatching Celery task for upload {confluence_upload.id}: {e}")
                return Response({"error": f"Failed to initiate import process after upload: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"ConfluenceImportView: Invalid data for file upload. User: {request.user.username if request.user else 'Unknown'}. Errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
