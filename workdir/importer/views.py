from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

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
        # Extract target IDs from request data (e.g., form data alongside the file)
        target_workspace_id_str = request.data.get('target_workspace_id')
        target_space_id_str = request.data.get('target_space_id')

        target_workspace_instance = None
        target_space_instance = None

        # Validate target_workspace_id if provided
        if target_workspace_id_str:
            if not Workspace:
                # This check is important if Workspace model itself failed to import
                return Response({"error": "Workspace functionality is currently unavailable."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            try:
                target_workspace_id = int(target_workspace_id_str)
                target_workspace_instance = Workspace.objects.get(pk=target_workspace_id)
                # TODO: Add permission check: Does request.user have access to this workspace?
                # e.g., if not target_workspace_instance.can_be_accessed_by(request.user): return Response(...)
            except ValueError:
                return Response({"error": "Invalid target_workspace_id format. Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
            except Workspace.DoesNotExist:
                return Response({"error": f"Target workspace with ID {target_workspace_id_str} not found."}, status=status.HTTP_404_NOT_FOUND)

        # Validate target_space_id if provided
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

        # Validate relationship if both workspace and space are explicitly provided
        if target_workspace_instance and target_space_instance:
            if target_space_instance.workspace != target_workspace_instance:
                return Response({"error": f"Target space '{target_space_instance.name}' does not belong to target workspace '{target_workspace_instance.name}'."}, status=status.HTTP_400_BAD_REQUEST)
        # If only space is provided, derive workspace from it (if space model has workspace FK)
        elif target_space_instance and not target_workspace_instance:
            if hasattr(target_space_instance, 'workspace') and target_space_instance.workspace:
                target_workspace_instance = target_space_instance.workspace
            else:
                # This case might indicate inconsistent data or setup if a space must have a workspace
                return Response({"error": f"Target space '{target_space_instance.name}' does not have an associated workspace."}, status=status.HTTP_400_BAD_REQUEST)

        # Serializer validates the 'file'. Other data for ConfluenceUpload is set here or by Celery task.
        upload_data_serializer = ConfluenceUploadSerializer(data=request.data)

        if upload_data_serializer.is_valid():
            # Save the ConfluenceUpload instance, now including target_workspace and target_space
            confluence_upload_instance = upload_data_serializer.save(
                user=request.user,
                target_workspace=target_workspace_instance, # Pass validated instance or None
                target_space=target_space_instance         # Pass validated instance or None
            )

            print(f"ConfluenceImportView: File uploaded. Record ID: {confluence_upload_instance.id}, User: {request.user.username}")
            if target_workspace_instance: print(f"  Target Workspace: {target_workspace_instance.name} (ID: {target_workspace_instance.id})")
            if target_space_instance: print(f"  Target Space: {target_space_instance.name} (ID: {target_space_instance.id})")

            try:
                import_confluence_space.delay(confluence_upload_id=confluence_upload_instance.id)

                # Re-serialize the instance to include fields like ID, status, and new target details
                # The ConfluenceUploadSerializer is already designed to show these details.
                response_serializer = ConfluenceUploadSerializer(confluence_upload_instance)
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
            # This will catch validation errors from the serializer (e.g., missing 'file')
            print(f"ConfluenceImportView: Invalid data for file upload. User: {request.user.username if request.user else 'Unknown'}. Errors: {upload_data_serializer.errors}")
            return Response(upload_data_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
