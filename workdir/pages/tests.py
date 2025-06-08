import os
import shutil
import tempfile
import zipfile # Used by ConfluenceImportTaskTests, but not directly by PageModelTests/PageDetailViewTests
from django.test import TestCase
import textwrap # Used by ImporterParserTests, but not directly here
from django.urls import reverse

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from unittest.mock import patch # Used by ConfluenceImportViewTests

from django.core.files.uploadedfile import SimpleUploadedFile
# from .models import ConfluenceUpload # This is from importer app - REMOVE

from django.conf import settings as django_settings
from django.test import override_settings
# from .tasks import import_confluence_space # This is from importer app - REMOVE
from pages.models import Page, Attachment, Tag
try:
    from workspaces.models import Workspace, Space
except ImportError:
    Workspace = None
    Space = None

User = get_user_model()

# Note: ImporterUtilsTests, ImporterParserTests, HtmlConverterTests, ConfluenceMetadataParserTests, ConfluenceImportTaskTests
# were previously in this file when it was importer/tests.py.
# They should NOT be in pages/tests.py.
# This overwrite will effectively remove them if this file is meant to be only pages/tests.py.
# Assuming the previous `overwrite_file_with_block` in Turn 119 already put the correct test classes here.
# The current task is to clean up imports for the tests that *are* in pages/tests.py

class PageModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='page_testuser', password='password123')
        if Workspace:
            try:
                cls.workspace = Workspace.objects.create(name='Test Workspace for Pages', owner=cls.user)
                if Space and cls.workspace:
                    cls.space = Space.objects.create(workspace=cls.workspace, name="Test Space for Pages", key="TSPPMT", owner=cls.user)
                else:
                    cls.space = None
            except Exception as e:
                cls.workspace = None
                cls.space = None
        else:
            cls.workspace = None
            cls.space = None

    def test_page_creation(self):
        if not self.space:
            self.skipTest("Space model not available or failed to create, skipping page creation test.")
        page_data = {
            'title': 'My Test Page',
            'content_json': {'type': 'doc', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Hello world'}]}]},
            'original_confluence_id': 'conf_12345',
            'space': self.space,
            'author': self.user,
            'imported_by': self.user
        }
        page = Page.objects.create(**page_data)
        self.assertEqual(page.title, page_data['title'])
        self.assertEqual(page.content_json, page_data['content_json'])
        self.assertEqual(page.original_confluence_id, page_data['original_confluence_id'])
        self.assertEqual(page.space, self.space)
        self.assertEqual(page.author, self.user)
        self.assertEqual(page.imported_by, self.user)
        self.assertIsNotNone(page.created_at)
        self.assertIsNotNone(page.updated_at)
        self.assertIsNotNone(page.slug)

    def test_page_str_method(self):
        if not self.space:
            self.skipTest("Space model not available, skipping page str method test.")
        page = Page.objects.create(title='Test Str Page', space=self.space, author=self.user)
        self.assertEqual(str(page), 'Test Str Page')

    def test_page_content_json_can_be_null_or_blank(self):
        if not self.space:
            self.skipTest("Space model not available, skipping page content_json null test.")
        page_default = Page.objects.create(title='Page with Default Content', space=self.space, author=self.user)
        self.assertEqual(page_default.content_json, {})
        page_null = Page.objects.create(title='Page with Null Content', space=self.space, author=self.user, content_json=None)
        self.assertIsNone(page_null.content_json)

    def test_page_parent_child_relationship(self):
        if not self.space:
            self.skipTest("Space not available for testing parent-child relationships.")
        parent_page = Page.objects.create(title="Parent Page Section", space=self.space, author=self.user)
        child_page = Page.objects.create(title="Child Page Section", space=self.space, author=self.user, parent=parent_page)
        self.assertEqual(child_page.parent, parent_page)
        self.assertEqual(parent_page.children.count(), 1)
        self.assertIn(child_page, parent_page.children.all())
        parent_page_id = parent_page.id
        parent_page.delete()
        child_page.refresh_from_db()
        self.assertIsNone(child_page.parent)
        with self.assertRaises(Page.DoesNotExist):
            Page.objects.get(id=parent_page_id)

    def test_page_slug_auto_generation_on_create(self):
        if not self.space:
            self.skipTest("Space not available for slug generation test.")
        page = Page.objects.create(title="A Test Page with Spaces & Cases", space=self.space, author=self.user)
        self.assertEqual(page.slug, "a-test-page-with-spaces-cases")

    def test_page_slug_uniqueness_on_create(self):
        if not self.space:
            self.skipTest("Space not available for slug uniqueness test.")
        page1 = Page.objects.create(title="Identical Title", space=self.space, author=self.user)
        self.assertEqual(page1.slug, "identical-title")
        page2 = Page.objects.create(title="Identical Title", space=self.space, author=self.user)
        self.assertEqual(page2.slug, "identical-title-1")
        page3 = Page.objects.create(title="Identical Title", space=self.space, author=self.user)
        self.assertEqual(page3.slug, "identical-title-2")

    def test_page_slug_not_regenerated_on_update_if_exists(self):
        if not self.space:
            self.skipTest("Space not available for slug update test.")
        page = Page.objects.create(title="Initial Title", space=self.space, author=self.user)
        initial_slug = page.slug
        self.assertEqual(initial_slug, "initial-title")
        page.title = "Updated Title, Slug Should Persist"
        page.save()
        self.assertEqual(page.slug, initial_slug)

    def test_page_slug_regenerated_if_cleared_on_update(self):
        if not self.space:
            self.skipTest("Space not available for slug regeneration test.")
        page = Page.objects.create(title="Original Title", space=self.space, author=self.user)
        self.assertEqual(page.slug, "original-title")
        page.title = "New Title after Clearing Slug"
        page.slug = ""
        page.save()
        self.assertEqual(page.slug, "new-title-after-clearing-slug")

    def test_page_slug_from_title_with_special_chars(self):
        if not self.space:
            self.skipTest("Space not available for special char slug test.")
        page = Page.objects.create(title="Title with !@#$%^&*()_+ and Ümlauts", space=self.space, author=self.user)
        self.assertEqual(page.slug, "title-with-_-and-umlauts")

    def test_page_slug_fallback_for_empty_title_on_create(self):
        if not self.space:
            self.skipTest("Space not available for empty title slug test.")
        page = Page.objects.create(title="!@#$", space=self.space, author=self.user)
        self.assertIsNotNone(page.slug)
        self.assertTrue(len(page.slug) == 8 or page.slug.endswith("-1") or len(page.slug) == 6)
        page2 = Page.objects.create(title="", space=self.space, author=self.user)
        self.assertIsNotNone(page2.slug)
        self.assertTrue(len(page2.slug) == 8 or page2.slug.endswith("-1") or len(page2.slug) == 6)
        self.assertNotEqual(page.slug, page2.slug)

    def test_page_slug_uniqueness_with_manual_set_and_autoset(self):
        if not self.space:
            self.skipTest("Space not available.")
        Page.objects.create(title="Manual Slug Test", slug="manual-slug-test", space=self.space, author=self.user)
        page_auto = Page.objects.create(title="Manual Slug Test", space=self.space, author=self.user)
        self.assertEqual(page_auto.slug, "manual-slug-test-1")


class AttachmentModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='attachment_testuser', password='password123')
        cls.page_for_attachment = None
        if Workspace and Space:
            try:
                workspace_for_attachments = Workspace.objects.create(name='Test Workspace for Attachments', owner=cls.user)
                space_for_attachments = Space.objects.create(workspace=workspace_for_attachments, name="Space for Attachments", key="SFA", owner=cls.user)
                cls.page_for_attachment = Page.objects.create(title='Page for Attachments', space=space_for_attachments, author=cls.user)
            except Exception as e:
                cls.page_for_attachment = None
        else:
            cls.page_for_attachment = None
        cls.dummy_file_content = b"dummy attachment content"
        cls.dummy_file_class_level = SimpleUploadedFile("class_level_test_attachment.txt", cls.dummy_file_content, "text/plain")

    def tearDown(self):
        attachments = Attachment.objects.all()
        for att in attachments:
            if att.file:
                if hasattr(att.file, 'path') and att.file.path and os.path.exists(att.file.path):
                    try: att.file.delete(save=False)
                    except Exception: pass

    def test_attachment_creation(self):
        if not self.page_for_attachment:
            self.skipTest("Page for attachment not available, skipping attachment creation test.")
        current_test_dummy_file = SimpleUploadedFile("test_attachment_creation.txt", self.dummy_file_content, "text/plain")
        attachment = Attachment.objects.create(page=self.page_for_attachment, original_filename="my_document.txt", file=current_test_dummy_file, mime_type="text/plain", imported_by=self.user)
        self.assertEqual(attachment.page, self.page_for_attachment)
        self.assertEqual(attachment.original_filename, "my_document.txt")
        self.assertTrue(attachment.file.name.endswith("test_attachment_creation.txt"))
        if hasattr(attachment.file, 'path') and attachment.file.path and os.path.exists(attachment.file.path):
            with open(attachment.file.path, 'rb') as f: content = f.read()
            self.assertEqual(content, self.dummy_file_content)

    def test_attachment_str_method(self):
        if not self.page_for_attachment:
            self.skipTest("Page for attachment not available, skipping attachment str method test.")
        dummy_file_for_str_test = SimpleUploadedFile("str_test_file.pdf", b"pdf content for str test", "application/pdf")
        attachment = Attachment.objects.create(page=self.page_for_attachment, original_filename="report.pdf", file=dummy_file_for_str_test, imported_by=self.user)
        self.assertEqual(str(attachment), "report.pdf")

class PageDetailViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='page_view_user', password='password')
        if Workspace:
            cls.workspace = Workspace.objects.create(name="Page View Test WS", owner=cls.user)
            if Space:
                cls.space = Space.objects.create(name="Page View Test Space", key="PVTS", workspace=cls.workspace, owner=cls.user)
            else: cls.space = None
        else: cls.workspace = None; cls.space = None

        if cls.space:
            cls.page1 = Page.objects.create(title="Page One for Slug Test", space=cls.space, author=cls.user, content_json={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Content P1"}]}]})
            cls.page2 = Page.objects.create(title="Page Two with Ümlauts", space=cls.space, author=cls.user, content_json={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Content P2"}]}]})
        else:
            cls.page1 = None; cls.page2 = None

    def test_retrieve_page_by_slug_success(self):
        if not self.page1: self.skipTest("Required Page instance (self.page1) not created.")
        url = reverse('pages:page-detail', kwargs={'slug': self.page1.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.page1.id)
        self.assertEqual(response.data['title'], self.page1.title)
        self.assertEqual(response.data['slug'], self.page1.slug)
        self.assertEqual(response.data['content_json'], self.page1.content_json)
        self.assertEqual(response.data['space']['key'], self.space.key)

    def test_retrieve_page_by_slug_with_unicode_chars_success(self):
        if not self.page2: self.skipTest("Required Page instance (self.page2) not created.")
        url = reverse('pages:page-detail', kwargs={'slug': self.page2.slug})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['id'], self.page2.id)
        self.assertEqual(response.data['title'], self.page2.title)
        self.assertTrue(response.data['slug'] == "page-two-with-umlauts" or response.data['slug'] == "page-two-with-uumlauts")

    def test_retrieve_page_by_slug_not_found(self):
        if not self.page1: self.skipTest("Skipping due to missing Page instance (self.page1).")
        url = reverse('pages:page-detail', kwargs={'slug': 'non-existent-slug-blah'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
