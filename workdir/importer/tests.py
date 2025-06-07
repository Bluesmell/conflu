import os
import shutil
import tempfile
import zipfile
from django.test import TestCase
import textwrap # Keep for dummy HTML content formatting within tests
# Assuming utils.py and parser.py are in the same app 'importer'
from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic

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
