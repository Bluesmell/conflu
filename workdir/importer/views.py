
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
# from .models import ConfluenceUpload # To be created later
from .tasks import import_confluence_space

class ConfluenceImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        print(f"ConfluenceImportView: Received POST request from user: {request.user.id}")

        placeholder_uploaded_file_id = request.data.get('uploaded_file_id', 1)
        user_id_to_pass = request.user.id

        try:
            import_confluence_space.delay(
                uploaded_file_id=placeholder_uploaded_file_id,
                user_id=user_id_to_pass
            )
            message = f"Confluence space import initiated for placeholder file ID: {placeholder_uploaded_file_id}."
            print(f"ConfluenceImportView: Dispatched task for user {user_id_to_pass}, placeholder_id {placeholder_uploaded_file_id}")
            return Response({"message": message}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            print(f"ConfluenceImportView: Error dispatching Celery task: {e}")
            return Response({"error": "Failed to initiate import process."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
