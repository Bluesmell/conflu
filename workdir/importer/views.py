from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.generics import RetrieveAPIView # Added for status view

from .models import ConfluenceUpload
from .serializers import ConfluenceUploadSerializer
from .tasks import import_confluence_space

# Import Workspace and Space for validation
try:
    from workspaces.models import Workspace, Space
except ImportError:
    Workspace = None
    Space = None
    print("WARNING: importer/views.py - Workspace/Space models not found. Target selection in ConfluenceImportView will be impaired.")

class ConfluenceImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        target_workspace_id_str = request.data.get('target_workspace_id')
        target_space_id_str = request.data.get('target_space_id')

        target_workspace_instance = None
        target_space_instance = None

        if target_workspace_id_str:
            if not Workspace:
                return Response({"error": "Workspace functionality is currently unavailable."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                target_workspace_id = int(target_workspace_id_str)
                target_workspace_instance = Workspace.objects.get(pk=target_workspace_id)
                # TODO: Add permission check: Does request.user have access to this workspace?
            except ValueError:
                return Response({"error": "Invalid target_workspace_id format. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            except Workspace.DoesNotExist:
                return Response({"error": f"Target workspace with ID {target_workspace_id_str} not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_space_id_str:
            if not Space:
                return Response({"error": "Space functionality is currently unavailable."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                target_space_id = int(target_space_id_str)
                target_space_instance = Space.objects.get(pk=target_space_id)
                # TODO: Add permission check for space access.
            except ValueError:
                return Response({"error": "Invalid target_space_id format. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            except Space.DoesNotExist:
                return Response({"error": f"Target space with ID {target_space_id_str} not found."}, status=status.HTTP_404_NOT_FOUND)

        if target_workspace_instance and target_space_instance:
            if target_space_instance.workspace != target_workspace_instance:
                return Response({"error": f"Target space '{target_space_instance.name}' does not belong to target workspace '{target_workspace_instance.name}'."}, status=status.HTTP_400_BAD_REQUEST)
        elif target_space_instance and not target_workspace_instance:
            if hasattr(target_space_instance, 'workspace') and target_space_instance.workspace:
                target_workspace_instance = target_space_instance.workspace
            else:
                return Response({"error": f"Target space '{target_space_instance.name}' does not have an associated workspace."}, status=status.HTTP_400_BAD_REQUEST)

        upload_data_serializer = ConfluenceUploadSerializer(data=request.data, context={'request': request})

        if upload_data_serializer.is_valid():
            confluence_upload_instance = upload_data_serializer.save(
                user=request.user,
                target_workspace=target_workspace_instance,
                target_space=target_space_instance
            )

            print(f"ConfluenceImportView: File uploaded. Record ID: {confluence_upload_instance.id}, User: {request.user.username}")
            if target_workspace_instance: print(f"  Target Workspace: {target_workspace_instance.name} (ID: {target_workspace_instance.id})")
            if target_space_instance: print(f"  Target Space: {target_space_instance.name} (ID: {target_space_instance.id})")

            try:
                import_confluence_space.delay(confluence_upload_id=confluence_upload_instance.id)

                response_serializer = ConfluenceUploadSerializer(confluence_upload_instance, context={'request': request})
                return Response({
                    "message": f"Confluence space import initiated for upload ID: {confluence_upload_instance.id}.",
                    "data": response_serializer.data
                }, status=status.HTTP_202_ACCEPTED)
            except Exception as e:
                confluence_upload_instance.status = ConfluenceUpload.STATUS_FAILED
                confluence_upload_instance.save()
                print(f"ConfluenceImportView: Critical error dispatching Celery task for upload {confluence_upload_instance.id}: {e}")
                return Response({"error": f"Failed to initiate import process after upload: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print(f"ConfluenceImportView: Invalid data for file upload. User: {request.user.username if request.user else 'Unknown'}. Errors: {upload_data_serializer.errors}")
            return Response(upload_data_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ConfluenceUploadStatusView(RetrieveAPIView):
    """
    API view to retrieve the status and progress of a ConfluenceUpload instance.
    """
    queryset = ConfluenceUpload.objects.all()
    serializer_class = ConfluenceUploadSerializer
    permission_classes = [IsAuthenticated] # Only authenticated users can check status
    lookup_field = 'pk'
    # TODO: Add object-level permission: only uploader or admin can see status.
    # For now, any authenticated user can see status of any upload by ID.

    # Ensure context is passed to serializer if it relies on request (e.g. for file_url)
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
