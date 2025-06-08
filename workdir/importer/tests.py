import os
import shutil
import tempfile
import zipfile
from django.test import TestCase
import textwrap # Keep for dummy HTML content formatting within tests
# Assuming utils.py and parser.py are in the same app 'importer'
from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic

# Added imports for ConfluenceImportViewTests
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

# Imports for updated tests and new model tests
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import ConfluenceUpload


class ImporterUtilsTests(TestCase):
    def setUp(self):
        # Create a unique base directory for all test files for this test class run
        self.base_temp_dir = tempfile.mkdtemp(prefix="importer_utils_tests_")

        self.dummy_zip_path = os.path.join(self.base_temp_dir, "test_export.zip")
        self.dummy_content_dir = os.path.join(self.base_temp_dir, "dummy_content_for_zip_utils")
        # Extraction target will be created by the utility function, ensure it's unique for tests
        self.extraction_target_dir = os.path.join(self.base_temp_dir, "test_extraction_temp_utils")

        os.makedirs(os.path.join(self.dummy_content_dir, "html_pages"), exist_ok=True)
        os.makedirs(os.path.join(self.dummy_content_dir, "assets"), exist_ok=True)

        with open(os.path.join(self.dummy_content_dir, "html_pages", "page1.html"), "w", encoding="utf-8") as f:
            f.write("<html><head><title>Page 1 Title</title></head><body><h1>Page 1 Heading</h1></body></html>")
        with open(os.path.join(self.dummy_content_dir, "html_pages", "page2.htm"), "w", encoding="utf-8") as f:
            f.write("<html><head><title>Page 2 Title</title></head><body><h1>Page 2 Heading</h1></body></html>")
        with open(os.path.join(self.dummy_content_dir, "entities.xml"), "w", encoding="utf-8") as f:
            f.write("<xml><meta>data</meta></xml>")

        with zipfile.ZipFile(self.dummy_zip_path, 'w') as zf:
            for root, _, files_in_root in os.walk(self.dummy_content_dir): # Renamed 'files'
                for file_in_zip in files_in_root:
                    file_path_in_zip = os.path.join(root, file_in_zip)
                    arcname = os.path.relpath(file_path_in_zip, self.dummy_content_dir)
                    zf.write(file_path_in_zip, arcname)

    def tearDown(self):
        shutil.rmtree(self.base_temp_dir)
        if os.path.exists("temp_confluence_export"): # Default name used by util if not specified
             shutil.rmtree("temp_confluence_export")

    def test_extract_html_and_metadata_from_zip_success(self):
        html_files, metadata_file = extract_html_and_metadata_from_zip(
            self.dummy_zip_path,
            temp_extract_dir=self.extraction_target_dir
        )
        self.assertEqual(len(html_files), 2)
        self.assertIsNotNone(metadata_file)
        extracted_html_names = sorted([os.path.basename(p) for p in html_files])
        self.assertEqual(extracted_html_names, sorted(["page1.html", "page2.htm"]))
        if metadata_file:
            self.assertEqual(os.path.basename(metadata_file), "entities.xml")

        self.assertTrue(os.path.exists(self.extraction_target_dir))
        cleanup_temp_extraction_dir(temp_extract_dir=self.extraction_target_dir)
        self.assertFalse(os.path.exists(self.extraction_target_dir))

    def test_extract_from_nonexistent_zip(self):
        html_files, metadata_file = extract_html_and_metadata_from_zip(
            "nonexistent_utils.zip", temp_extract_dir=self.extraction_target_dir
        )
        self.assertEqual(len(html_files), 0)
        self.assertIsNone(metadata_file)
        self.assertFalse(os.path.exists(self.extraction_target_dir))

    def test_extract_from_bad_zip(self):
        bad_zip_path = os.path.join(self.base_temp_dir, "bad_utils.zip")
        with open(bad_zip_path, "w", encoding="utf-8") as f: f.write("this is not a zip file")
        html_files, metadata_file = extract_html_and_metadata_from_zip(
            bad_zip_path, temp_extract_dir=self.extraction_target_dir
        )
        self.assertEqual(len(html_files), 0)
        self.assertIsNone(metadata_file)
        self.assertFalse(os.path.exists(self.extraction_target_dir))

class ImporterParserTests(TestCase):
    def setUp(self):
        self.base_temp_dir = tempfile.mkdtemp(prefix="importer_parser_tests_")
        self.dummy_html_path = os.path.join(self.base_temp_dir, "test_page_for_parser.html")

        # Use textwrap.dedent for the HTML content string for clarity
        dummy_html_content_for_file = textwrap.dedent("""
        <html>
        <head><title> My Parser Test Page </title></head>
        <body>
            <h1>First Heading</h1>
            <p>First paragraph.</p>
            <h1>Second Heading with <span>Nested Span</span></h1>
            <p>Second paragraph with <b>bold</b>.</p>
            <p>Third paragraph.</p>
        </body>
        </html>
        """)
        with open(self.dummy_html_path, "w", encoding="utf-8") as f:
            f.write(dummy_html_content_for_file)

    def tearDown(self):
        shutil.rmtree(self.base_temp_dir)

    def test_parse_html_file_basic_success(self):
        parsed_data = parse_html_file_basic(self.dummy_html_path)
        self.assertIsNotNone(parsed_data)
        self.assertEqual(parsed_data.get("title"), "My Parser Test Page")
        self.assertListEqual(sorted(parsed_data.get("h1_tags")), sorted(["First Heading", "Second Heading with Nested Span"]))
        self.assertEqual(len(parsed_data.get("paragraphs_sample")), 3)
        self.assertEqual(parsed_data.get("paragraphs_sample")[0], "First paragraph.")

    def test_parse_nonexistent_html_file(self):
        parsed_data = parse_html_file_basic(os.path.join(self.base_temp_dir,"nonexistent_parser_test.html"))
        self.assertIsNone(parsed_data)

class ConfluenceImportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser_importer_view', password='password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.import_url = "/api/v1/io/import/confluence/"

    @patch('workdir.importer.views.import_confluence_space.delay')
    def test_post_request_triggers_import_task(self, mock_import_task_delay):
        # Create a dummy ZIP file for upload
        dummy_file_content = b"This is a dummy zip file content."
        dummy_file = SimpleUploadedFile(
            "test_confluence_export.zip",
            dummy_file_content,
            content_type="application/zip"
        )
        payload = {'file': dummy_file}

        response = self.client.post(self.import_url, data=payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)

        # Check that a ConfluenceUpload record was created
        self.assertEqual(ConfluenceUpload.objects.count(), 1)
        created_upload_record = ConfluenceUpload.objects.first()
        self.assertIsNotNone(created_upload_record)
        self.assertEqual(created_upload_record.user, self.user)
        self.assertTrue(created_upload_record.file.name.endswith(".zip")) # Check if file field is populated
        self.assertEqual(created_upload_record.status, ConfluenceUpload.STATUS_PENDING) # Initial status

        # Check that the Celery task was called once with the correct ID
        mock_import_task_delay.assert_called_once()
        args, kwargs = mock_import_task_delay.call_args
        self.assertEqual(kwargs.get('confluence_upload_id'), created_upload_record.id)

        # Check response data
        self.assertIn('data', response.data)
        self.assertEqual(response.data['data']['id'], created_upload_record.id)
        self.assertEqual(response.data['data']['status'], ConfluenceUpload.STATUS_PENDING)

        # Clean up the uploaded file from storage after test
        if created_upload_record and created_upload_record.file:
            created_upload_record.file.delete(save=False)


class ConfluenceUploadModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testmodeluser', password='password')
        self.dummy_file = SimpleUploadedFile(
            "model_test.zip",
            b"dummy content for model test",
            "application/zip"
        )

    def tearDown(self):
        # Clean up any files created by ConfluenceUpload instances
        uploads = ConfluenceUpload.objects.all()
        for upload in uploads:
            if upload.file:
                upload.file.delete(save=False)

    def test_confluence_upload_creation(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)
        self.assertEqual(upload.user, self.user)
        # File name might be prefixed with upload_to path, so check endswith
        self.assertTrue(upload.file.name.endswith("model_test.zip"))
        self.assertEqual(upload.status, ConfluenceUpload.STATUS_PENDING)
        self.assertIsNotNone(upload.uploaded_at)
        self.assertIsNone(upload.task_id) # Initially null

    def test_confluence_upload_str_method(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)
        # Based on the model's __str__ method:
        # f"Import ID {self.pk or 'Unsaved'} ({file_name}) by {username} - Status: {self.get_status_display()}"
        expected_filename = os.path.basename(upload.file.name) # Model uses os.path.basename
        expected_str = f"Import ID {upload.pk} ({expected_filename}) by {self.user.username} - Status: Pending"
        self.assertEqual(str(upload), expected_str)

    def test_confluence_upload_status_choices(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)

        upload.status = ConfluenceUpload.STATUS_PROCESSING
        upload.save()
        self.assertEqual(upload.get_status_display(), "Processing")

        upload.status = ConfluenceUpload.STATUS_COMPLETED
        upload.save()
        self.assertEqual(upload.get_status_display(), "Completed")

        upload.status = ConfluenceUpload.STATUS_FAILED
        upload.save()
        self.assertEqual(upload.get_status_display(), "Failed")


class EnhancedHtmlParserTests(TestCase):
    def setUp(self):
        # Create a temporary directory to store dummy HTML files for tests
        self.temp_dir = tempfile.mkdtemp(prefix="parser_tests_enhanced_") # Changed prefix for clarity

    def tearDown(self):
        # Remove the temporary directory and its contents after tests
        shutil.rmtree(self.temp_dir)

    def _create_dummy_html_file(self, filename, content):
        """Helper to create a temporary HTML file with given content."""
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_parse_simple_page_with_main_content_div(self):
        html_content = """
        <html><head><title>Simple Page</title></head>
        <body>
            <div id="main-content">
                <h1>Main Heading</h1><p>Some text. <img src="../attachments/image.png"></p>
                <a href="attachments/doc.pdf">Document</a>
            </div>
            <div id="footer">Footer stuff</div>
        </body></html>
        """
        file_path = self._create_dummy_html_file("simple.html", html_content)
        result = parse_html_file_basic(file_path) # parse_html_file_basic is the enhanced one now

        self.assertIsNotNone(result)
        self.assertEqual(result.get("title"), "Simple Page")
        # More robust checks for main_content_html
        main_html = result.get("main_content_html", "")
        self.assertIn("<h1>Main Heading</h1>", main_html)
        self.assertTrue("<img src=\"../attachments/image.png\"/>" in main_html or "<img src=\"../attachments/image.png\">" in main_html)
        self.assertIn("<a href=\"attachments/doc.pdf\">Document</a>", main_html)
        self.assertNotIn("Footer stuff", main_html)
        self.assertEqual(sorted(result.get("referenced_attachments", [])), sorted(["doc.pdf", "image.png"]))


    def test_parse_with_wiki_content_class(self):
        html_content = """
        <html><head><title>Wiki Page</title></head>
        <body>
            <div class="wiki-content">
                <p>Content here. <img src="image2.jpg"></p>
            </div>
        </body></html>
        """
        file_path = self._create_dummy_html_file("wiki.html", html_content)
        result = parse_html_file_basic(file_path)
        self.assertEqual(result.get("title"), "Wiki Page")
        main_html = result.get("main_content_html", "")
        self.assertTrue("<img src=\"image2.jpg\"/>" in main_html or "<img src=\"image2.jpg\">" in main_html)
        self.assertIn("<p>Content here. ", main_html)
        self.assertEqual(result.get("referenced_attachments"), ["image2.jpg"])

    def test_parse_fallback_to_body_if_no_main_div(self):
        html_content = """
        <html><head><title>Body Fallback</title></head>
        <body>
            <h1>Only Body Content</h1>
            <p>An attachment: <a href="files/report.docx">Report</a></p>
        </body></html>
        """
        file_path = self._create_dummy_html_file("body_fallback.html", html_content)
        result = parse_html_file_basic(file_path)
        self.assertEqual(result.get("title"), "Body Fallback")
        main_html = result.get("main_content_html", "")
        self.assertIn("<h1>Only Body Content</h1>", main_html)
        self.assertIn("<a href=\"files/report.docx\">Report</a>", main_html)
        self.assertEqual(result.get("referenced_attachments"), ["report.docx"])

    def test_attachment_extraction_various_paths_and_encoded(self):
        html_content = """
        <html><head><title>Attachments Test</title></head>
        <body><div id="main-content">
            <img src="simple.gif"/>
            <img src="../attachments/complex name with spaces.png"/>
            <a href="attachments/My%20Document.pdf">My PDF</a>
            <a href="externalhttp://example.com/doc.txt">External</a>
            <a href="#anchor">Anchor link</a>
            <img src="data:image/png;base64,..." />
        </div></body></html>
        """
        file_path = self._create_dummy_html_file("attachments.html", html_content)
        result = parse_html_file_basic(file_path)
        expected_attachments = sorted(["My Document.pdf", "complex name with spaces.png", "simple.gif"])
        self.assertEqual(sorted(result.get("referenced_attachments", [])), expected_attachments)

    def test_no_attachments(self):
        html_content = """
        <html><head><title>No Attachments</title></head>
        <body><div id="main-content"><p>Just text.</p></div></body></html>
        """
        file_path = self._create_dummy_html_file("no_attachments.html", html_content)
        result = parse_html_file_basic(file_path)
        self.assertEqual(result.get("referenced_attachments", []), [])

    def test_title_fallback_to_h1(self):
        html_content = """
        <html><head></head><body>
        <div id="main-content"><h1>Actual Page Title</h1><p>Text.</p></div>
        </body></html>
        """
        file_path = self._create_dummy_html_file("h1_title.html", html_content)
        result = parse_html_file_basic(file_path)
        self.assertEqual(result.get("title"), "Actual Page Title")

    def test_file_not_found(self):
        result = parse_html_file_basic(os.path.join(self.temp_dir, "nonexistent.html"))
        self.assertIsNone(result)

    def test_parsing_error_returns_partial_data_with_error_key(self):
        # Test with a file that's not HTML (e.g. binary), which might cause issues.
        binary_content = b"\x00\x01\x02\x03\x04\xff\xfe\xfd"
        file_path_bin = self._create_dummy_html_file("binary_file.html", binary_content.decode('latin-1', errors='ignore'))
        result_bin = parse_html_file_basic(file_path_bin)

        self.assertIsNotNone(result_bin)
        self.assertIn("error", result_bin)
        # Title might be None or some default depending on how BS4 handles very broken content for title tag.
        # For a binary file, it's likely title extraction also fails or yields empty/None.
        self.assertIsNone(result_bin.get("title")) # Expect title to be None if parsing fails very early
        self.assertIsNone(result_bin.get("main_content_html"))
        self.assertEqual(result_bin.get("referenced_attachments", []), [])


from .converter import convert_html_to_prosemirror_json # Function to test

class HtmlConverterTests(TestCase):
    def test_empty_and_none_html(self):
        self.assertEqual(convert_html_to_prosemirror_json(""), {"type": "doc", "content": []})
        self.assertEqual(convert_html_to_prosemirror_json(None), {"type": "doc", "content": []})

    def test_simple_paragraph(self):
        html = "<p>Hello world.</p>"
        expected_json = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Hello world."}]}
            ]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)


from .parser import parse_confluence_metadata_for_hierarchy

class ConfluenceMetadataParserTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="metadata_parser_tests_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _create_dummy_xml_file(self, filename, content):
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_parse_simple_hierarchy(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>100</long></property><property name="title"><string>Parent</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>101</long></property><property name="title"><string>Child</string></property>
                <property name="parent"><id>100</id></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("simple.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        self.assertEqual(len(result), 2)
        expected_child = {'id': '101', 'title': 'Child', 'parent_id': '100'}
        expected_parent = {'id': '100', 'title': 'Parent', 'parent_id': None}
        self.assertIn(expected_child, result)
        self.assertIn(expected_parent, result)

    def test_parse_no_parent_for_top_level(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>200</long></property><property name="title"><string>Top Level Page</string></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("toplevel.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {'id': '200', 'title': 'Top Level Page', 'parent_id': None})

    def test_parse_nested_parent_object_id_format(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>300</long></property><property name="title"><string>Parent 300</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>301</long></property><property name="title"><string>Child 301</string></property>
                <property name="parent"><object class="Page"><property name="id"><long>300</long></property></object></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("nested_parent.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        expected_child = {'id': '301', 'title': 'Child 301', 'parent_id': '300'}
        self.assertIn(expected_child, result)

    def test_parse_parent_page_property_format(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>400</long></property><property name="title"><string>Parent 400</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>401</long></property><property name="title"><string>Child 401</string></property>
                <property name="parentPage"><id>400</id></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("parentpage_prop.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        expected_child = {'id': '401', 'title': 'Child 401', 'parent_id': '400'}
        self.assertIn(expected_child, result)

    def test_parse_empty_xml_or_no_pages(self):
        xml_content_empty = "<hibernate-generic></hibernate-generic>"
        xml_content_no_pages = "<hibernate-generic><object class='Space'></object></hibernate-generic>"
        file_path_empty = self._create_dummy_xml_file("empty.xml", xml_content_empty)
        file_path_no_pages = self._create_dummy_xml_file("no_pages.xml", xml_content_no_pages)

        self.assertEqual(parse_confluence_metadata_for_hierarchy(file_path_empty), [])
        self.assertEqual(parse_confluence_metadata_for_hierarchy(file_path_no_pages), [])

    def test_parse_file_not_found(self):
        self.assertEqual(parse_confluence_metadata_for_hierarchy("nonexistent.xml"), [])

    def test_parse_malformed_xml(self):
        xml_content = "<unclosed>Malformed XML"
        file_path = self._create_dummy_xml_file("malformed.xml", xml_content)
        self.assertEqual(parse_confluence_metadata_for_hierarchy(file_path), [])


from .parser import parse_confluence_metadata_for_hierarchy

class ConfluenceMetadataParserTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="metadata_parser_tests_")

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def _create_dummy_xml_file(self, filename, content):
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path

    def test_parse_simple_hierarchy(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>100</long></property><property name="title"><string>Parent</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>101</long></property><property name="title"><string>Child</string></property>
                <property name="parent"><id>100</id></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("simple.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        self.assertEqual(len(result), 2)
        expected_child = {'id': '101', 'title': 'Child', 'parent_id': '100'}
        expected_parent = {'id': '100', 'title': 'Parent', 'parent_id': None}
        self.assertIn(expected_child, result)
        self.assertIn(expected_parent, result)

    def test_parse_no_parent_for_top_level(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>200</long></property><property name="title"><string>Top Level Page</string></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("toplevel.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {'id': '200', 'title': 'Top Level Page', 'parent_id': None})

    def test_parse_nested_parent_object_id_format(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>300</long></property><property name="title"><string>Parent 300</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>301</long></property><property name="title"><string>Child 301</string></property>
                <property name="parent"><object class="Page"><property name="id"><long>300</long></property></object></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("nested_parent.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        expected_child = {'id': '301', 'title': 'Child 301', 'parent_id': '300'}
        self.assertIn(expected_child, result)

    def test_parse_parent_page_property_format(self):
        xml_content = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>400</long></property><property name="title"><string>Parent 400</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>401</long></property><property name="title"><string>Child 401</string></property>
                <property name="parentPage"><id>400</id></property>
            </object>
        </hibernate-generic>
        """
        file_path = self._create_dummy_xml_file("parentpage_prop.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        expected_child = {'id': '401', 'title': 'Child 401', 'parent_id': '400'}
        self.assertIn(expected_child, result)

    def test_parse_empty_xml_or_no_pages(self):
        xml_content_empty = "<hibernate-generic></hibernate-generic>"
        xml_content_no_pages = "<hibernate-generic><object class='Space'></object></hibernate-generic>"
        file_path_empty = self._create_dummy_xml_file("empty.xml", xml_content_empty)
        file_path_no_pages = self._create_dummy_xml_file("no_pages.xml", xml_content_no_pages)

        self.assertEqual(parse_confluence_metadata_for_hierarchy(file_path_empty), [])
        self.assertEqual(parse_confluence_metadata_for_hierarchy(file_path_no_pages), [])

    def test_parse_file_not_found(self):
        self.assertEqual(parse_confluence_metadata_for_hierarchy("nonexistent.xml"), [])

    def test_parse_malformed_xml(self):
        xml_content = "<unclosed>Malformed XML"
        file_path = self._create_dummy_xml_file("malformed.xml", xml_content)
        self.assertEqual(parse_confluence_metadata_for_hierarchy(file_path), [])


# Imports for ConfluenceImportTaskTests (some might be duplicates from top, ensure organized)
# zipfile, tempfile, shutil, os are already imported at the top or by other test classes.
# User, SimpleUploadedFile, ConfluenceUpload are also imported above.
# Page, Attachment from pages.models (Attachment already imported by HtmlConverterTests, Page not yet explicitly for other tests)
from django.conf import settings as django_settings # Renamed to avoid conflict if 'settings' is used as var
from django.test import override_settings
# from django.core.files.base import ContentFile # Not used in final version of task tests
from .tasks import import_confluence_space # The Celery task
from pages.models import Page, Attachment # Page needs to be imported here if not already
try:
    from workspaces.models import Workspace, Space
except ImportError:
    Workspace = None
    Space = None


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ConfluenceImportTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='task_testuser', password='password123')

        if Workspace:
            cls.workspace = Workspace.objects.create(name='Task Test Workspace', owner=cls.user)
            if Space:
                # Assuming Space model has 'created_by' or similar if user is passed.
                # Based on pages/models.py, Space is just 'name' and 'workspace'.
                cls.space = Space.objects.create(name='Task Test Space', workspace=cls.workspace)
            else:
                cls.space = None
        else:
            cls.workspace = None
            cls.space = None

        if not cls.workspace or not cls.space:
            print("ConfluenceImportTaskTests: Workspace/Space models not available or setup failed. Some tests will be skipped.")

    def setUp(self):
        self.temp_media_dir_obj = tempfile.TemporaryDirectory(prefix="test_media_")
        self.temp_media_dir_path = self.temp_media_dir_obj.name

        self.original_media_root = django_settings.MEDIA_ROOT
        django_settings.MEDIA_ROOT = self.temp_media_dir_path

        self.zip_temp_dir_obj = tempfile.TemporaryDirectory(prefix="zip_creation_")
        self.zip_temp_dir_path = self.zip_temp_dir_obj.name

    def tearDown(self):
        django_settings.MEDIA_ROOT = self.original_media_root
        self.temp_media_dir_obj.cleanup()
        self.zip_temp_dir_obj.cleanup()

    def _create_dummy_confluence_zip(self, zip_filename, html_files_data=None,
                                   attachment_files_data=None, create_attachments_subfolder=False,
                                   metadata_xml_content=None): # New parameter
        html_files_data = html_files_data or {}
        attachment_files_data = attachment_files_data or {}

        zip_file_path = os.path.join(self.zip_temp_dir_path, zip_filename) # Corrected to use self.zip_temp_dir_path
        current_zip_content_dir = tempfile.mkdtemp(dir=self.zip_temp_dir_path) # Corrected to use self.zip_temp_dir_path

        for name, content in html_files_data.items():
            file_path = os.path.join(current_zip_content_dir, name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

        attachments_root_in_zip = current_zip_content_dir
        if create_attachments_subfolder:
            attachments_root_in_zip = os.path.join(current_zip_content_dir, "attachments")
            os.makedirs(attachments_root_in_zip, exist_ok=True)
        for name, content in attachment_files_data.items():
            file_path = os.path.join(attachments_root_in_zip, name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "wb") as f:
                f.write(content)

        if metadata_xml_content:
            metadata_filepath = os.path.join(current_zip_content_dir, "entities.xml")
            with open(metadata_filepath, "w", encoding="utf-8") as f:
                f.write(metadata_xml_content)

        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, _, files_in_dir in os.walk(current_zip_content_dir):
                for file_item in files_in_dir:
                    full_path = os.path.join(root_dir, file_item)
                    arcname = os.path.relpath(full_path, current_zip_content_dir)
                    zf.write(full_path, arcname)

        shutil.rmtree(current_zip_content_dir)
        return zip_file_path

    def test_import_task_success_simple_page_no_attachments(self):
        if not self.workspace or not self.space:
            self.skipTest("Workspace or Space not available for testing.")

        html_data = {"page1_123.html": "<html><head><title>Test Page 1</title></head><body><div id='main-content'><p>Content of page 1</p></div></body></html>"}
        zip_path = self._create_dummy_confluence_zip("test1.zip", html_files_data=html_data)

        with open(zip_path, 'rb') as f_zip:
            upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=f_zip.read(), content_type='application/zip')

        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        result_message = import_confluence_space(confluence_upload_id=upload_record.id)

        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)

        self.assertTrue(Page.objects.filter(space=self.space, title="Test Page 1", original_confluence_id="123").exists())
        page1 = Page.objects.get(original_confluence_id="123", space=self.space)
        self.assertEqual(page1.imported_by, self.user)
        self.assertIsNotNone(page1.content_json)
        self.assertEqual(page1.content_json['type'], 'doc')
        # Based on current converter for "<p>Content of page 1</p>"
        expected_content = [{"type": "paragraph", "content": [{"type": "text", "text": "Content of page 1"}]}]
        self.assertEqual(page1.content_json['content'], expected_content)
        self.assertEqual(Attachment.objects.count(), 0)
        self.assertIn("Pages created: 1", result_message)


    def test_import_task_page_with_attachments(self):
        if not self.workspace or not self.space:
            self.skipTest("Workspace or Space not available for testing.")

        html_content = "<html><head><title>Page With Attach</title></head><body><div id='main-content'><p>See <img src='../attachments/image.png'> and <a href='doc.pdf'>doc</a>.</p></div></body></html>"
        html_data = {"pages/page_attach_789.html": html_content} # HTML in a subfolder

        attachment_data_in_zip_attachments_folder = {"image.png": b"img_content_zip"}
        attachment_data_in_zip_root = {"doc.pdf": b"pdf_content_zip"}

        zip_path = self._create_dummy_confluence_zip(
            "test_attach.zip",
            html_files_data=html_data,
            attachment_files_data=attachment_data_in_zip_attachments_folder,
            create_attachments_subfolder=True # This puts image.png under 'attachments/'
        )
        with zipfile.ZipFile(zip_path, 'a') as zf:
            for name, content in attachment_data_in_zip_root.items():
                 zf.writestr(name, content) # Add doc.pdf to root

        with open(zip_path, 'rb') as f_zip:
            upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=f_zip.read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)

        result_message = import_confluence_space(confluence_upload_id=upload_record.id)

        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED, result_message)
        self.assertTrue(Page.objects.filter(original_confluence_id="789", space=self.space).exists())
        page = Page.objects.get(original_confluence_id="789", space=self.space)

        self.assertEqual(Attachment.objects.filter(page=page).count(), 2)

        img_attach = Attachment.objects.get(page=page, original_filename="image.png")
        pdf_attach = Attachment.objects.get(page=page, original_filename="doc.pdf")

        self.assertTrue(img_attach.file.name.endswith("image.png"))
        self.assertTrue(pdf_attach.file.name.endswith("doc.pdf"))
        with img_attach.file.open('rb') as f:
            self.assertEqual(f.read(), b"img_content_zip")
        with pdf_attach.file.open('rb') as f:
            self.assertEqual(f.read(), b"pdf_content_zip")
        self.assertIn("Pages created: 1", result_message)

    def test_import_task_no_html_files_in_zip(self):
        zip_path = self._create_dummy_confluence_zip("no_html.zip", attachment_files_data={"text.txt": b"data"})
        with open(zip_path, 'rb') as f_zip:
            upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=f_zip.read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)

        import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db()

        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_FAILED)
        self.assertEqual(Page.objects.count(), 0)

    def test_import_task_with_page_hierarchy(self):
        if not self.workspace or not self.space:
            self.skipTest("Workspace or Space not available for testing hierarchy.")

        sample_metadata_xml = """
        <hibernate-generic>
            <object class="Page">
                <property name="id"><long>100</long></property>
                <property name="title"><string>Parent Page H</string></property>
            </object>
            <object class="Page">
                <property name="id"><long>101</long></property>
                <property name="title"><string>Child Page H1</string></property>
                <property name="parent"><id>100</id></property>
            </object>
            <object class="Page">
                <property name="id"><long>102</long></property>
                <property name="title"><string>Child Page H2</string></property>
                <property name="parent"><id>100</id></property>
            </object>
             <object class="Page">
                <property name="id"><long>103</long></property>
                <property name="title"><string>Grandchild Page H1.1</string></property>
                <property name="parent"><id>101</id></property>
            </object>
        </hibernate-generic>
        """

        html_data = {
            "Parent_Page_H_100.html": "<html><head><title>Parent Page H</title></head><body><div id='main-content'><p>Parent content</p></div></body></html>",
            "Child_Page_H1_101.html": "<html><head><title>Child Page H1</title></head><body><div id='main-content'><p>Child 1 content</p></div></body></html>",
            "Child_Page_H2_102.html": "<html><head><title>Child Page H2</title></head><body><div id='main-content'><p>Child 2 content</p></div></body></html>",
            "Grandchild_Page_H1.1_103.html": "<html><head><title>Grandchild Page H1.1</title></head><body><div id='main-content'><p>Grandchild 1.1 content</p></div></body></html>"
        }

        zip_path = self._create_dummy_confluence_zip(
            "test_hierarchy.zip",
            html_files_data=html_data,
            metadata_xml_content=sample_metadata_xml
        )

        with open(zip_path, 'rb') as f_zip:
            upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=f_zip.read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)

        result_message = import_confluence_space(confluence_upload_id=upload_record.id)

        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        self.assertIn("Pages created: 4", result_message)
        self.assertTrue(Page.objects.count() == 4)

        parent_h = Page.objects.get(original_confluence_id="100", space=self.space)
        child_h1 = Page.objects.get(original_confluence_id="101", space=self.space)
        child_h2 = Page.objects.get(original_confluence_id="102", space=self.space)
        grandchild_h1_1 = Page.objects.get(original_confluence_id="103", space=self.space)

        self.assertEqual(parent_h.title, "Parent Page H")
        self.assertEqual(child_h1.title, "Child Page H1")
        self.assertEqual(child_h2.title, "Child Page H2")
        self.assertEqual(grandchild_h1_1.title, "Grandchild Page H1.1")

        self.assertIsNone(parent_h.parent)
        self.assertEqual(child_h1.parent, parent_h)
        self.assertEqual(child_h2.parent, parent_h)
        self.assertEqual(grandchild_h1_1.parent, child_h1)

        self.assertCountEqual(list(parent_h.children.all()), [child_h1, child_h2])
        self.assertCountEqual(list(child_h1.children.all()), [grandchild_h1_1])
        self.assertEqual(child_h2.children.count(), 0)
        self.assertEqual(grandchild_h1_1.children.count(), 0)
