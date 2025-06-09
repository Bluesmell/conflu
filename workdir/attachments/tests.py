from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from pages.models import Page
from workspaces.models import Space
from .models import Attachment
from guardian.shortcuts import assign_perm, remove_perm

class AttachmentAPIPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.uploader = User.objects.create_user(username='uploader', password='password123')
        cls.other_user = User.objects.create_user(username='otheruser_attach', password='password123')

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        models_and_perms_for_uploader = {
            Space: ['add_space'],
            Page: ['add_page'],
            Attachment: ['add_attachment', 'change_attachment', 'delete_attachment', 'view_attachment'] # Add view_attachment model perm
        }

        for model_cls, perm_codenames in models_and_perms_for_uploader.items():
            content_type = ContentType.objects.get_for_model(model_cls)
            for codename in perm_codenames:
                try:
                    perm = Permission.objects.get(content_type=content_type, codename=codename)
                    cls.uploader.user_permissions.add(perm)
                except Permission.DoesNotExist:
                    print(f"DEBUG: Warning: {codename} permission for {model_cls._meta.model_name} not found for uploader.")

        # Grant other_user model-level view_attachment permission to test 403 vs 404 logic
        # If a user has model-level view but not object-level view, they should get 403.
        # If they lack model-level view, has_permission might fail earlier or has_object_permission might result in 404.
        # For this test, other_user will NOT have model-level view_attachment initially.

        cls.space = Space.objects.create(key='ATTACHSPACE', name='Attachment Test Space', owner=cls.uploader)
        cls.page = Page.objects.create(
            space=cls.space, title='Page for Attachments',
            content_json={'type':'doc'}, author=cls.uploader, version=1
        )
        assign_perm('pages.view_page', cls.other_user, cls.page) # Object perm for page

    def setUp(self):
        self.client_uploader = APIClient()
        self.client_uploader.force_authenticate(user=self.uploader)

        self.client_other_user = APIClient()
        self.client_other_user.force_authenticate(user=self.other_user)

        self.anon_client = APIClient()

        self.dummy_file = SimpleUploadedFile("test_attachment.txt", b"Test file content.", content_type="text/plain")
        self.attachment_data = {
            'page': self.page.pk,
            'file_name': 'test_attachment.txt',
            'file': self.dummy_file
        }
        response_upload = self.client_uploader.post(reverse('attachment-list'), self.attachment_data, format='multipart')

        error_message = ""
        if response_upload.status_code != status.HTTP_201_CREATED:
            try:
                error_message = response_upload.json()
            except Exception:
                error_message = response_upload.content
        self.assertEqual(response_upload.status_code, status.HTTP_201_CREATED,
                         f"Failed to upload attachment in setUp. User: {self.uploader.username}. Response: {error_message}")
        self.attachment1 = Attachment.objects.get(pk=response_upload.data['id'])
        self.attachment1_detail_url = reverse('attachment-detail', kwargs={'pk': self.attachment1.pk})
        self.attachment1_download_url = reverse('attachment-download', kwargs={'pk': self.attachment1.pk})

        self.attachment1.scan_status = 'clean'
        self.attachment1.save()

    def test_uploader_can_delete_attachment(self):
        response = self.client_uploader.delete(self.attachment1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_uploader_cannot_delete_attachment(self):
        response = self.client_other_user.delete(self.attachment1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_uploader_can_download_attachment(self): # Uploader has obj view perm from perform_create
        response = self.client_uploader.get(self.attachment1_download_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/octet-stream')

    def test_non_uploader_cannot_download_attachment_without_explicit_perm(self):
        # other_user does not have model-level 'view_attachment' and no object-level 'view_attachment'
        # DjangoObjectPermissions.has_object_permission raises Http404 in this case for SAFE_METHODS
        response = self.client_other_user.get(self.attachment1_download_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Changed from 403 to 404

    def test_user_with_view_attachment_perm_can_download(self):
        # Give other_user object-level view permission
        assign_perm('attachments.view_attachment', self.other_user, self.attachment1)
        # To get 200, other_user also needs model-level view_attachment because has_permission() checks it first for authenticated users.
        # However, our ExtendedDjangoObjectPermissionsOrAnonReadOnly.has_permission allows SAFE methods for all authenticated.
        # So only object perm is needed.
        response = self.client_other_user.get(self.attachment1_download_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        remove_perm('attachments.view_attachment', self.other_user, self.attachment1)

    def test_anon_cannot_download_attachment(self):
        # AnonymousUser does not have model-level 'view_attachment' and no object-level 'view_attachment'
        # DjangoObjectPermissions.has_object_permission raises Http404 in this case for SAFE_METHODS
        response = self.anon_client.get(self.attachment1_download_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Changed from 403 to 404
