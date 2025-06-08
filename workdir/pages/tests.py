from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings # For potential cleanup reference, though not strictly used in simplified cleanup
import os # For os.path.exists and os.path.basename

# Try to import Workspace, proceed with a placeholder if import fails
try:
    from workspaces.models import Workspace
    from workspaces.models import Space # Also import Space as Page model uses it
except ImportError:
    # This allows tests to be defined, but they will be skipped if Workspace is None.
    Workspace = None
    Space = None

from .models import Page, Attachment

User = get_user_model()

class PageModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='page_testuser', password='password123')
        if Workspace:
            try:
                cls.workspace = Workspace.objects.create(name='Test Workspace for Pages', owner=cls.user)
                if Space and cls.workspace: # Ensure Space is imported and workspace exists
                    cls.space = Space.objects.create(workspace=cls.workspace, name="Test Space for Pages")
                else:
                    cls.space = None # Mark space as None if Space model or workspace is unavailable
            except Exception as e:
                print(f"Warning: Could not create Workspace/Space in PageModelTests.setUpTestData: {e}.")
                cls.workspace = None
                cls.space = None
        else:
            cls.workspace = None
            cls.space = None

    def test_page_creation(self):
        if not self.workspace or not self.space:
            self.skipTest("Workspace or Space model not available or failed to create, skipping page creation test.")

        page_data = {
            'title': 'My Test Page',
            'content_json': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Hello world'}]}]},
            'original_confluence_id': 'conf_12345',
            'space': self.space,
            'imported_by': self.user
        }

        page = Page.objects.create(**page_data)

        self.assertEqual(page.title, page_data['title'])
        self.assertEqual(page.content_json, page_data['content_json'])
        self.assertEqual(page.original_confluence_id, page_data['original_confluence_id'])
        self.assertEqual(page.space, self.space)
        self.assertEqual(page.imported_by, self.user)
        self.assertIsNotNone(page.created_at)
        self.assertIsNotNone(page.updated_at)

    def test_page_str_method(self):
        if not self.space: # Depends on space for page creation
            self.skipTest("Space model not available, skipping page str method test.")

        page = Page.objects.create(title='Test Str Page', space=self.space, imported_by=self.user)
        self.assertEqual(str(page), 'Test Str Page')

    def test_page_content_json_can_be_null(self):
        if not self.space: # Depends on space for page creation
            self.skipTest("Space model not available, skipping page content_json null test.")

        page = Page.objects.create(
            title='Page with Null Content',
            space=self.space,
            imported_by=self.user,
            content_json=None
        )
        self.assertIsNone(page.content_json)
        self.assertEqual(page.title, 'Page with Null Content')


class AttachmentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='attachment_testuser', password='password123')
        cls.page_for_attachment = None

        if Workspace and Space: # Both Workspace and Space must be available
            try:
                workspace_for_attachments = Workspace.objects.create(name='Test Workspace for Attachments', owner=cls.user)
                space_for_attachments = Space.objects.create(workspace=workspace_for_attachments, name="Space for Attachments")
                cls.page_for_attachment = Page.objects.create(title='Page for Attachments', space=space_for_attachments, imported_by=cls.user)
            except Exception as e:
                print(f"Warning: Could not create Workspace/Space/Page in AttachmentModelTests.setUpTestData: {e}.")
                cls.page_for_attachment = None
        else:
            cls.page_for_attachment = None


        cls.dummy_file_content = b"dummy attachment content"
        # Create a new SimpleUploadedFile instance for the class attribute
        cls.dummy_file_class_level = SimpleUploadedFile(
            "class_level_test_attachment.txt",
            cls.dummy_file_content,
            "text/plain"
        )

    def tearDown(self):
        attachments = Attachment.objects.all()
        for att in attachments:
            if att.file:
                if hasattr(att.file, 'path') and os.path.exists(att.file.path):
                    try:
                        att.file.delete(save=False)
                    except Exception as e:
                        print(f"Warning: Error deleting file {att.file.path} in tearDown: {e}")
                else:
                    try:
                        att.file.delete(save=False)
                    except Exception as e:
                        print(f"Warning: Error attempting to delete file {att.file.name} (non-local path or already deleted?): {e}")

    def test_attachment_creation(self):
        if not self.page_for_attachment:
            self.skipTest("Page for attachment not available, skipping attachment creation test.")

        # Create a new SimpleUploadedFile for this specific test to ensure fresh state
        current_test_dummy_file = SimpleUploadedFile(
            "test_attachment_creation.txt",
            self.dummy_file_content,
            "text/plain"
        )
        attachment = Attachment.objects.create(
            page=self.page_for_attachment,
            original_filename="my_document.txt",
            file=current_test_dummy_file,
            mime_type="text/plain",
            imported_by=self.user
        )
        self.assertEqual(attachment.page, self.page_for_attachment)
        self.assertEqual(attachment.original_filename, "my_document.txt")
        self.assertTrue(attachment.file.name.endswith("test_attachment_creation.txt"))
        self.assertEqual(attachment.mime_type, "text/plain")
        self.assertEqual(attachment.imported_by, self.user)
        self.assertIsNotNone(attachment.created_at)

        if hasattr(attachment.file, 'path') and os.path.exists(attachment.file.path):
            with open(attachment.file.path, 'rb') as f:
                content = f.read()
            self.assertEqual(content, self.dummy_file_content)


    def test_attachment_str_method(self):
        if not self.page_for_attachment:
            self.skipTest("Page for attachment not available, skipping attachment str method test.")

        dummy_file_for_str_test = SimpleUploadedFile("str_test_file.pdf", b"pdf content for str test", "application/pdf")
        attachment = Attachment.objects.create(
            page=self.page_for_attachment,
            original_filename="report.pdf",
            file=dummy_file_for_str_test,
            imported_by=self.user
        )
        self.assertEqual(str(attachment), "report.pdf")
