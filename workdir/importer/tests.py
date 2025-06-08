import os
import shutil
import tempfile
import zipfile
from django.test import TestCase
import textwrap # Keep for dummy HTML content formatting within tests
# Assuming utils.py and parser.py are in the same app 'importer'
from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic, parse_confluence_metadata_for_hierarchy
from .converter import convert_html_to_prosemirror_json

from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from .models import ConfluenceUpload

from django.conf import settings as django_settings
from django.test import override_settings
from .tasks import import_confluence_space
from pages.models import Page, Attachment
try:
    from workspaces.models import Workspace, Space
except ImportError:
    Workspace = None
    Space = None


class ImporterUtilsTests(TestCase):
    def setUp(self):
        self.base_temp_dir = tempfile.mkdtemp(prefix="importer_utils_tests_")
        self.dummy_zip_path = os.path.join(self.base_temp_dir, "test_export.zip")
        self.dummy_content_dir = os.path.join(self.base_temp_dir, "dummy_content_for_zip_utils")
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
            for root, _, files_in_root in os.walk(self.dummy_content_dir):
                for file_in_zip in files_in_root:
                    file_path_in_zip = os.path.join(root, file_in_zip)
                    arcname = os.path.relpath(file_path_in_zip, self.dummy_content_dir)
                    zf.write(file_path_in_zip, arcname)
    def tearDown(self):
        shutil.rmtree(self.base_temp_dir)
        if hasattr(self, 'extraction_target_dir') and os.path.exists(self.extraction_target_dir): # Ensure it exists before cleanup
            cleanup_temp_extraction_dir(temp_extract_dir=self.extraction_target_dir) # Call the actual cleanup util
        # Fallback for older temp_confluence_export name, if any test created it directly
        if os.path.exists("temp_confluence_export"):
             shutil.rmtree("temp_confluence_export")

    def test_extract_html_and_metadata_from_zip_success(self):
        html_files, metadata_file = extract_html_and_metadata_from_zip(self.dummy_zip_path,temp_extract_dir=self.extraction_target_dir)
        self.assertEqual(len(html_files), 2)
        self.assertIsNotNone(metadata_file)
        extracted_html_names = sorted([os.path.basename(p) for p in html_files])
        self.assertEqual(extracted_html_names, sorted(["page1.html", "page2.htm"]))
        if metadata_file: self.assertEqual(os.path.basename(metadata_file), "entities.xml")
        self.assertTrue(os.path.exists(self.extraction_target_dir))
        cleanup_temp_extraction_dir(temp_extract_dir=self.extraction_target_dir) # Test cleanup
        self.assertFalse(os.path.exists(self.extraction_target_dir))

    def test_extract_from_nonexistent_zip(self):
        html_files, metadata_file = extract_html_and_metadata_from_zip("nonexistent_utils.zip", temp_extract_dir=self.extraction_target_dir)
        self.assertEqual(len(html_files), 0)
        self.assertIsNone(metadata_file)
        self.assertFalse(os.path.exists(self.extraction_target_dir)) # Should not create dir if zip doesn't exist

    def test_extract_from_bad_zip(self):
        bad_zip_path = os.path.join(self.base_temp_dir, "bad_utils.zip")
        with open(bad_zip_path, "w", encoding="utf-8") as f: f.write("this is not a zip file")
        html_files, metadata_file = extract_html_and_metadata_from_zip(bad_zip_path, temp_extract_dir=self.extraction_target_dir)
        self.assertEqual(len(html_files), 0)
        self.assertIsNone(metadata_file)
        self.assertFalse(os.path.exists(self.extraction_target_dir)) # Should not create dir if zip is bad


class ImporterParserTests(TestCase):
    def setUp(self):
        self.base_temp_dir = tempfile.mkdtemp(prefix="importer_parser_tests_")
        self.dummy_html_path = os.path.join(self.base_temp_dir, "test_page_for_parser.html")
        dummy_html_content_for_file = textwrap.dedent("""
        <html><head><title> My Parser Test Page </title></head><body>
            <h1>First Heading</h1><p>First paragraph.</p>
            <h1>Second Heading with <span>Nested Span</span></h1>
            <p>Second paragraph with <b>bold</b>.</p><p>Third paragraph.</p>
        </body></html>""")
        with open(self.dummy_html_path, "w", encoding="utf-8") as f: f.write(dummy_html_content_for_file)
    def tearDown(self): shutil.rmtree(self.base_temp_dir)

    def test_parse_html_file_basic_success(self):
        parsed_data = parse_html_file_basic(self.dummy_html_path)
        self.assertIsNotNone(parsed_data)
        self.assertEqual(parsed_data.get("title"), "My Parser Test Page")

    def test_parse_nonexistent_html_file(self):
        self.assertIsNone(parse_html_file_basic(os.path.join(self.base_temp_dir,"nonexistent.html")))


class ConfluenceUploadModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testmodeluser', password='password')
        self.dummy_file = SimpleUploadedFile("model.zip", b"content", "application/zip")
        if Workspace: # Create workspace and space for tests that need them
            self.ws_for_model_test = Workspace.objects.create(name="WS for Model Test", owner=self.user)
            if Space:
                self.space_for_model_test = Space.objects.create(name="Space for Model Test", key="SMT", workspace=self.ws_for_model_test, owner=self.user)


    def tearDown(self):
        # Clean up files from FileField
        for upload in ConfluenceUpload.objects.all():
            if upload.file:
                if os.path.exists(upload.file.path): # Check if file exists before trying to delete
                    upload.file.delete(save=False) # save=False to avoid re-saving model during cleanup
        # Clean up test Workspaces and Spaces if created
        if hasattr(self, 'ws_for_model_test'):
            self.ws_for_model_test.delete()


    def test_confluence_upload_creation(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)
        self.assertTrue(upload.file.name.endswith("model.zip"))
        self.assertEqual(upload.status, ConfluenceUpload.STATUS_PENDING)
        self.assertIsNone(upload.target_workspace) # Check default for new fields
        self.assertIsNone(upload.target_space)

    def test_confluence_upload_str_method(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)
        self.assertIn(str(upload.pk), str(upload))
        self.assertIn(self.user.username, str(upload))

    def test_confluence_upload_with_target_workspace_and_space(self):
        if not Workspace or not Space:
            self.skipTest("Workspace or Space models not available for this test.")

        # Use instances created in setUp
        ws = self.ws_for_model_test
        space = self.space_for_model_test

        upload_with_target = ConfluenceUpload.objects.create(
            user=self.user,
            file=self.dummy_file,
            target_workspace=ws,
            target_space=space
        )
        self.assertEqual(upload_with_target.target_workspace, ws)
        self.assertEqual(upload_with_target.target_space, space)


class ConfluenceImportViewTests(TestCase):
    def setUp(self):
        # super().setUp() # Not inheriting from a common base with setUp
        self.user = User.objects.create_user(username='view_testuser_targets', password='password')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.import_url = "/api/v1/io/import/confluence/" # Ensure this URL is registered in urls.py

        # Create workspaces and spaces for view tests
        if Workspace:
            self.workspace1 = Workspace.objects.create(name="WS1 for View Test", owner=self.user)
            if Space:
                self.space1_ws1 = Space.objects.create(name="Space1 in WS1", key="S1W1VW", workspace=self.workspace1, owner=self.user)
            self.workspace2 = Workspace.objects.create(name="WS2 for View Test", owner=self.user)
            if Space:
                self.space1_ws2 = Space.objects.create(name="Space1 in WS2", key="S1W2VW", workspace=self.workspace2, owner=self.user)
        else: # Set to None if models aren't available, tests relying on them will be skipped.
            self.workspace1 = None
            self.space1_ws1 = None
            self.workspace2 = None
            self.space1_ws2 = None
            print("ConfluenceImportViewTests: Workspace/Space models not available. Some view tests might be skipped or fail if they rely on these models.")

    def tearDown(self):
        # Clean up files from FileField
        ConfluenceUpload.objects.all().delete() # Ensures files are handled by model's custom delete if any, or signals
        # Clean up test Workspaces and Spaces
        if hasattr(self, 'workspace1') and self.workspace1: self.workspace1.delete()
        if hasattr(self, 'workspace2') and self.workspace2: self.workspace2.delete()
        # Spaces are cascade-deleted with workspaces.

    @patch('importer.views.import_confluence_space.delay')
    def test_post_request_triggers_import_task(self, mock_delay): # This tests fallback target logic
        dummy_file = SimpleUploadedFile("test.zip", b"content", "application/zip")
        response = self.client.post(self.import_url, {'file': dummy_file}, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertEqual(ConfluenceUpload.objects.count(), 1)
        upload = ConfluenceUpload.objects.first()
        self.assertIsNone(upload.target_workspace) # No targets specified by client
        self.assertIsNone(upload.target_space)
        mock_delay.assert_called_once_with(confluence_upload_id=upload.id)

    @patch('importer.views.import_confluence_space.delay')
    def test_import_view_with_target_workspace_and_space_success(self, mock_delay):
        if not self.workspace1 or not self.space1_ws1:
            self.skipTest("Workspace/Space not available for target selection test.")

        dummy_zip_content = b"dummy zip for target test"
        test_file = SimpleUploadedFile("target_test.zip", dummy_zip_content, "application/zip")

        payload = {
            'file': test_file,
            'target_workspace_id': self.workspace1.id,
            'target_space_id': self.space1_ws1.id
        }
        response = self.client.post(self.import_url, data=payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        self.assertEqual(ConfluenceUpload.objects.count(), 1)
        upload_record = ConfluenceUpload.objects.first()
        self.assertEqual(upload_record.target_workspace, self.workspace1)
        self.assertEqual(upload_record.target_space, self.space1_ws1)
        mock_delay.assert_called_once_with(confluence_upload_id=upload_record.id)

    @patch('importer.views.import_confluence_space.delay')
    def test_import_view_with_only_target_workspace_success(self, mock_delay):
        if not self.workspace1:
            self.skipTest("Workspace not available for target selection test.")

        test_file = SimpleUploadedFile("ws_target_test.zip", b"zip content", "application/zip")
        payload = {'file': test_file, 'target_workspace_id': self.workspace1.id}
        response = self.client.post(self.import_url, data=payload, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED, response.data)
        upload_record = ConfluenceUpload.objects.first()
        self.assertEqual(upload_record.target_workspace, self.workspace1)
        self.assertIsNone(upload_record.target_space) # Space was not specified by client
        mock_delay.assert_called_once_with(confluence_upload_id=upload_record.id)

    @patch('importer.views.import_confluence_space.delay')
    def test_import_view_invalid_target_workspace_id(self, mock_delay):
        test_file = SimpleUploadedFile("invalid_ws.zip", b"c", "application/zip")
        payload = {'file': test_file, 'target_workspace_id': 99999} # Non-existent ID
        response = self.client.post(self.import_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_delay.assert_not_called() # Task should not be called

    @patch('importer.views.import_confluence_space.delay')
    def test_import_view_invalid_target_space_id(self, mock_delay):
        test_file = SimpleUploadedFile("invalid_sp.zip", b"c", "application/zip")
        payload = {'file': test_file, 'target_space_id': 88888} # Non-existent ID
        response = self.client.post(self.import_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        mock_delay.assert_not_called() # Task should not be called

    @patch('importer.views.import_confluence_space.delay')
    def test_import_view_space_not_in_workspace_error(self, mock_delay):
        if not self.workspace1 or not self.space1_ws2: # space1_ws2 belongs to workspace2
            self.skipTest("Workspace/Space setup not available for cross-match test.")

        test_file = SimpleUploadedFile("cross_match.zip", b"c", "application/zip")
        payload = {
            'file': test_file,
            'target_workspace_id': self.workspace1.id,
            'target_space_id': self.space1_ws2.id # This space is in workspace2
        }
        response = self.client.post(self.import_url, data=payload, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("does not belong to target workspace", response.data.get('error', '').lower())
        mock_delay.assert_not_called() # Task should not be called


class EnhancedHtmlParserTests(TestCase): # Keep existing tests below as they are
    def setUp(self): self.temp_dir = tempfile.mkdtemp(prefix="parser_enhanced_")
    def tearDown(self): shutil.rmtree(self.temp_dir)
    def _create_dummy_html_file(self, name, content):
        p = os.path.join(self.temp_dir, name);
        with open(p, "w", encoding="utf-8") as f: f.write(content)
        return p
    def test_simple_page_main_content(self):
        html = "<html><head><title>S</title></head><body><div id='main-content'><h1>H</h1><p>T <img src='../a/i.png'></p><a href='a/d.pdf'>D</a></div><div id='footer'>F</div></body></html>"
        r = parse_html_file_basic(self._create_dummy_html_file("s.html", html))
        self.assertEqual(r.get("title"), "S"); self.assertIn("<h1>H</h1>", r.get("main_content_html",""))
        self.assertNotIn("F", r.get("main_content_html","")); self.assertEqual(sorted(r.get("referenced_attachments",[])), sorted(["i.png","d.pdf"]))
    def test_parse_with_wiki_content_class(self):
        html = "<html><head><title>W</title></head><body><div class='wiki-content'><p>C <img src='i.jpg'></p></div></body></html>"
        r = parse_html_file_basic(self._create_dummy_html_file("w.html", html)); self.assertEqual(r.get("title"),"W")
        self.assertIn("<p>C ",r.get("main_content_html","")); self.assertEqual(r.get("referenced_attachments"),["i.jpg"])
    def test_title_fallback_to_h1(self):
        r = parse_html_file_basic(self._create_dummy_html_file("h.html","<html><body><div id='main-content'><h1>T</h1></div></body></html>"))
        self.assertEqual(r.get("title"),"T")
    def test_file_not_found(self): self.assertIsNone(parse_html_file_basic("nonexistent.html"))
    def test_parsing_error_returns_dict_with_error(self):
        r = parse_html_file_basic(self._create_dummy_html_file("b.html", b"\0\1\2".decode('latin-1',errors='ignore')))
        self.assertIsNotNone(r); self.assertIn("error",r)

class HtmlConverterTests(TestCase):
    def test_empty_and_none_html(self):
        self.assertEqual(convert_html_to_prosemirror_json(""), {"type": "doc", "content": []})
        self.assertEqual(convert_html_to_prosemirror_json(None), {"type": "doc", "content": []})
    def test_simple_paragraph(self):
        self.assertEqual(convert_html_to_prosemirror_json("<p>H</p>"), {"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"H"}]}]})
    def test_headings(self):
        self.assertEqual(convert_html_to_prosemirror_json("<h1>H1</h1>"), {"type":"doc","content":[{"type":"heading","attrs":{"level":1},"content":[{"type":"text","text":"H1"}]}]})
    def test_marks(self):
        r = convert_html_to_prosemirror_json("<p><strong>b</strong><em>i</em></p>")['content'][0]['content']
        self.assertEqual(r[0],{"type":"text","marks":[{"type":"bold"}],"text":"b"})
        self.assertEqual(r[1],{"type":"text","marks":[{"type":"italic"}],"text":"i"})
    def test_nested_marks(self):
        r = convert_html_to_prosemirror_json("<p><strong><em>bi</em></strong></p>")['content'][0]['content'][0]
        self.assertEqual(r['text'],'bi'); self.assertIn({"type":"bold"},r['marks']); self.assertIn({"type":"italic"},r['marks'])
    def test_link_mark(self):
        self.assertEqual(convert_html_to_prosemirror_json('<p><a href="u">t</a></p>')['content'][0]['content'][0], {"type":"text","marks":[{"type":"link","attrs":{"href":"u"}}],"text":"t"})
    def test_hard_break(self):
        self.assertEqual(convert_html_to_prosemirror_json("<p>1<br>2</p>")['content'][0]['content'], [{"type":"text","text":"1"},{"type":"hard_break"},{"type":"text","text":"2"}])
    def test_lists(self):
        self.assertEqual(convert_html_to_prosemirror_json("<ul><li>I1</li></ul>")['content'][0], {"type":"bullet_list","content":[{"type":"list_item","content":[{"type":"paragraph", "content":[{"type":"text","text":"I1"}]}]}]})
        self.assertEqual(convert_html_to_prosemirror_json("<ol><li>I1</li></ol>")['content'][0], {"type":"ordered_list","content":[{"type":"list_item","content":[{"type":"paragraph", "content":[{"type":"text","text":"I1"}]}]}]})
    def test_list_item_with_paragraph(self):
        self.assertEqual(convert_html_to_prosemirror_json("<ul><li><p>I1</p></li></ul>")['content'][0]['content'][0], {"type":"list_item","content":[{"type":"paragraph","content":[{"type":"text","text":"I1"}]}]})
    def test_unmapped_tags_unwrapped(self):
        self.assertEqual(convert_html_to_prosemirror_json("<div><p>P</p></div>")['content'], [{"type":"paragraph","content":[{"type":"text","text":"P"}]}])
    def test_top_level_text_wrapped(self):
        self.assertEqual(convert_html_to_prosemirror_json("T")['content'],[{"type":"paragraph","content":[{"type":"text","text":"T"}]}])
    def test_empty_p_omitted_or_empty_content(self):
        expected_empty_p_output = [{"type": "paragraph", "content": []}]
        self.assertEqual(convert_html_to_prosemirror_json("<p></p>")['content'], expected_empty_p_output)
        self.assertEqual(convert_html_to_prosemirror_json("<p>  </p>")['content'], expected_empty_p_output)

    def test_simple_table(self):
        html = "<table><tr><td>R1C1</td><td>R1C2</td></tr><tr><td>R2C1</td><td>R2C2</td></tr></table>"
        json_output = convert_html_to_prosemirror_json(html)
        self.assertEqual(json_output['content'][0]['type'], 'table')
        self.assertEqual(len(json_output['content'][0]['content']), 2)
        self.assertEqual(json_output['content'][0]['content'][0]['content'][0]['content'][0]['content'][0]['text'], 'R1C1')
    def test_table_with_headers_and_sections(self):
        html = "<table><thead><tr><th>H1</th></tr></thead><tbody><tr><td>C1</td></tr></tbody></table>"
        json_output = convert_html_to_prosemirror_json(html)
        self.assertEqual(json_output['content'][0]['content'][0]['content'][0]['type'], 'table_header')
        self.assertEqual(json_output['content'][0]['content'][1]['content'][0]['type'], 'table_cell')
    def test_table_cell_col_row_span(self):
        html = '<table><tr><td colspan="2" rowspan="3">M</td></tr></table>'
        attrs = convert_html_to_prosemirror_json(html)['content'][0]['content'][0]['content'][0]['attrs']
        self.assertEqual(attrs, {'colspan': 2, 'rowspan': 3})
    def test_empty_table_cell(self):
        html = "<table><tr><td></td></tr></table>"
        cell = convert_html_to_prosemirror_json(html)['content'][0]['content'][0]['content'][0]
        self.assertEqual(cell['content'], [{'type':'paragraph', 'content':[]}])

    def test_image_conversion(self):
        html = '<p><img src="img.png" alt="Alt" title="Title"></p>'
        img_node = convert_html_to_prosemirror_json(html)['content'][0]['content'][0]
        self.assertEqual(img_node['type'], 'image')
        self.assertEqual(img_node['attrs'], {'src':'pm:attachment:img.png', 'alt':'Alt', 'title':'Title'})
    def test_image_no_src_skipped(self):
        self.assertEqual(convert_html_to_prosemirror_json("<p><img></p>")['content'][0]['content'],[])

    def test_simple_task_list(self):
        html = '<ul class="task-list"><li class="task-list-item" data-task-status="complete">Done</li><li class="task-list-item" data-task-status="incomplete">Todo</li></ul>'
        json_output = convert_html_to_prosemirror_json(html)
        self.assertEqual(json_output['content'][0]['type'], 'task_list')
        task_list = json_output['content'][0]['content']
        self.assertEqual(len(task_list), 2)
        self.assertEqual(task_list[0]['type'], 'task_item')
        self.assertEqual(task_list[0]['attrs']['checked'], True)
        self.assertEqual(task_list[0]['content'][0]['content'][0]['text'], 'Done')
        self.assertEqual(task_list[1]['attrs']['checked'], False)
        self.assertEqual(task_list[1]['content'][0]['content'][0]['text'], 'Todo')

    def test_task_item_with_formatted_text(self):
        html = '<ul class="task-list"><li class="task-list-item" data-task-status="incomplete"><span class="task-item-body">Task <strong>bold</strong></span></li></ul>'
        task_item_p_content = convert_html_to_prosemirror_json(html)['content'][0]['content'][0]['content'][0]['content']
        self.assertEqual(task_item_p_content[0]['text'], 'Task ')
        self.assertEqual(task_item_p_content[1]['marks'][0]['type'], 'bold')

    def test_code_block_simple(self):
        html = "<pre>print('Hello')\n  line2</pre>"
        expected = {"type":"doc","content":[{"type":"code_block","content":[{"type":"text","text":"print('Hello')\n  line2"}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected)

    def test_code_block_with_language_class(self):
        html = '<pre class="language-python">def f(): pass</pre>'
        expected = {"type":"doc","content":[{"type":"code_block","attrs":{"language":"python"},"content":[{"type":"text","text":"def f(): pass"}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected)

    def test_code_block_with_brush_class(self):
        html = '<pre class="brush: java; gutter: false;">System.out.println();</pre>'
        expected = {"type":"doc","content":[{"type":"code_block","attrs":{"language":"java"},"content":[{"type":"text","text":"System.out.println();"}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected)

    def test_empty_code_block(self):
        html = "<pre></pre>"
        expected = {"type":"doc","content":[{"type":"code_block", "content": [{"type":"text", "text": ""}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected)

    def test_horizontal_rule(self):
        html = "<hr>"
        expected_json = {"type": "doc", "content": [{"type": "horizontal_rule"}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_horizontal_rule_xml_self_closing(self):
        html = "<hr />"
        expected_json = {"type": "doc", "content": [{"type": "horizontal_rule"}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_horizontal_rule_with_surrounding_paragraphs(self):
        html = "<p>Above</p><hr><p>Below</p>"
        expected_json = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Above"}]},{"type": "horizontal_rule"},{"type": "paragraph", "content": [{"type": "text", "text": "Below"}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_multiple_horizontal_rules(self):
        html = "<hr><hr/>"
        expected_json = {"type": "doc", "content": [{"type": "horizontal_rule"},{"type": "horizontal_rule"}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_simple_blockquote(self):
        html = "<blockquote><p>Quoted text here.</p></blockquote>"
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Quoted text here."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_with_multiple_paragraphs(self):
        html = "<blockquote><p>First para.</p><p>Second para.</p></blockquote>"
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "First para."}]},{"type": "paragraph", "content": [{"type": "text", "text": "Second para."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_empty_blockquote(self):
        html = "<blockquote></blockquote>"
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "content": [{"type": "paragraph", "content": []}] }]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_with_inline_marks_in_paragraph(self):
        html = "<blockquote><p>Quote with <strong>bold</strong> text.</p></blockquote>"
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Quote with "},{"type": "text", "marks": [{"type": "bold"}], "text": "bold"},{"type": "text", "text": " text."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_with_direct_text_content_is_wrapped(self):
        html = "<blockquote>This text is directly in the blockquote.</blockquote>"
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "This text is directly in the blockquote."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_containing_list(self):
        html = "<blockquote><ul><li>Item 1</li></ul></blockquote>"
        json_output = convert_html_to_prosemirror_json(html)
        self.assertEqual(json_output['type'], 'doc')
        self.assertEqual(len(json_output['content']), 1)
        blockquote_node = json_output['content'][0]
        self.assertEqual(blockquote_node['type'], 'blockquote')
        self.assertTrue(len(blockquote_node.get('content', [])) >= 1, "Blockquote content should not be empty")
        list_node = blockquote_node['content'][0]
        self.assertEqual(list_node['type'], 'bullet_list')
        self.assertEqual(len(list_node.get('content', [])), 1)
        list_item_node = list_node['content'][0]
        self.assertEqual(list_item_node['type'], 'list_item')
        self.assertEqual(list_item_node['content'][0]['type'], 'paragraph')
        self.assertEqual(list_item_node['content'][0]['content'][0]['text'], 'Item 1')

    def test_confluence_info_panel(self):
        html = """<div class="confluence-information-macro confluence-information-macro-information"><div class="confluence-information-macro-body"><p>This is an info panel.</p></div></div>"""
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "attrs": {"panelType": "info"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "This is an info panel."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_confluence_note_panel_with_direct_text(self):
        html = """<div class="confluence-information-macro confluence-information-macro-note"><div class="confluence-information-macro-body">Note text here.</div></div>"""
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "attrs": {"panelType": "note"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Note text here."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_confluence_warning_panel_with_list(self):
        html = """<div class="confluence-information-macro confluence-information-macro-warning"><div class="confluence-information-macro-body"><ul><li>Warning item 1</li></ul></div></div>"""
        json_output = convert_html_to_prosemirror_json(html)
        self.assertEqual(json_output['type'], 'doc')
        panel_node = json_output['content'][0]
        self.assertEqual(panel_node['type'], 'blockquote')
        self.assertEqual(panel_node.get('attrs', {}).get('panelType'), 'warning')
        self.assertTrue(len(panel_node['content']) > 0, "Panel content should not be empty")
        list_node = panel_node['content'][0]
        self.assertEqual(list_node['type'], 'bullet_list')
        self.assertEqual(list_node['content'][0]['content'][0]['content'][0]['text'], 'Warning item 1')

    def test_confluence_tip_panel_empty_body(self):
        html = """<div class="confluence-information-macro confluence-information-macro-tip"><div class="confluence-information-macro-body"></div></div>"""
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "attrs": {"panelType": "tip"}, "content": [{"type": "paragraph", "content": []}] }]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_panel_div_only_base_class_is_unwrapped(self):
        html = """<div class="confluence-information-macro"><p>Content of a generic panel-like div.</p></div>"""
        expected_json = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Content of a generic panel-like div."}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_panel_with_title_div_is_ignored(self):
        html = """<div class="confluence-information-macro confluence-information-macro-note"><div class="confluence-information-macro-title">This is a Title</div><div class="confluence-information-macro-body"><p>Actual content.</p></div></div>"""
        expected_json = {"type": "doc", "content": [{"type": "blockquote", "attrs": {"panelType": "note"}, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Actual content."}]}]}]}
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)


class ConfluenceMetadataParserTests(TestCase):
    def setUp(self): self.temp_dir = tempfile.mkdtemp(prefix="metadata_parser_tests_")
    def tearDown(self): shutil.rmtree(self.temp_dir)
    def _create_dummy_xml_file(self, filename, content):
        file_path = os.path.join(self.temp_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f: f.write(content)
        return file_path
    def test_parse_simple_hierarchy(self):
        xml_content = """<hibernate-generic><object class="Page"><property name="id"><long>100</long></property><property name="title"><string>Parent</string></property></object><object class="Page"><property name="id"><long>101</long></property><property name="title"><string>Child</string></property><property name="parent"><id>100</id></property></object></hibernate-generic>"""
        file_path = self._create_dummy_xml_file("simple.xml", xml_content)
        result = parse_confluence_metadata_for_hierarchy(file_path)
        self.assertIn({'id': '101', 'title': 'Child', 'parent_id': '100'}, result)
        self.assertIn({'id': '100', 'title': 'Parent', 'parent_id': None}, result)
    def test_parse_no_parent_for_top_level(self):
        xml_content = """<hibernate-generic><object class="Page"><property name="id"><long>200</long></property><property name="title"><string>Top</string></property></object></hibernate-generic>"""
        result = parse_confluence_metadata_for_hierarchy(self._create_dummy_xml_file("t.xml", xml_content))
        self.assertEqual(result[0], {'id': '200', 'title': 'Top', 'parent_id': None})
    def test_parse_file_not_found(self): self.assertEqual(parse_confluence_metadata_for_hierarchy("n.xml"), [])
    def test_parse_malformed_xml(self): self.assertEqual(parse_confluence_metadata_for_hierarchy(self._create_dummy_xml_file("m.xml", "<u")), [])


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class ConfluenceImportTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='task_target_user', password='password123')
        if Workspace:
            cls.ws_default = Workspace.objects.create(name='Task Default WS', owner=cls.user)
            cls.ws_target = Workspace.objects.create(name='Task Target WS', owner=cls.user)
            if Space:
                cls.space_default_in_ws_default = Space.objects.create(name='Default Space in Default WS', key="DSDWS", workspace=cls.ws_default, owner=cls.user)
                cls.space_target_in_ws_target = Space.objects.create(name='Target Space in Target WS', key="TSTWS", workspace=cls.ws_target, owner=cls.user)
                cls.space_alt_in_ws_target = Space.objects.create(name='Alt Space in Target WS', key="ASTWS", workspace=cls.ws_target, owner=cls.user)
            else: # Space model not available
                cls.space_default_in_ws_default = None
                cls.space_target_in_ws_target = None
                cls.space_alt_in_ws_target = None
        else: # Workspace model not available
            cls.ws_default = None
            cls.ws_target = None
            cls.space_default_in_ws_default = None
            cls.space_target_in_ws_target = None
            cls.space_alt_in_ws_target = None

        # Print a warning if models are not available, as tests might be skipped.
        if not cls.ws_default or not cls.space_default_in_ws_default:
            print("ConfluenceImportTaskTests.setUpTestData: Default Workspace/Space models not available. Some task tests might be skipped.")


    def setUp(self):
        self.temp_media_dir_obj = tempfile.TemporaryDirectory(prefix="test_media_")
        self.temp_media_dir_path = self.temp_media_dir_obj.name
        # django_settings.MEDIA_ROOT = self.temp_media_dir_path # Careful with overriding global settings directly
        # Instead, use override_settings decorator if needed per test or class, or ensure MEDIA_ROOT is test-friendly
        self.zip_temp_dir_obj = tempfile.TemporaryDirectory(prefix="zip_creation_")
        self.zip_temp_dir_path = self.zip_temp_dir_obj.name

        # Use a specific media root for this test class if files are actually written to disk by model's FileField
        # For ConfluenceUpload, 'file' field stores to 'confluence_imports/%Y/%m/%d/'
        # So, ensure MEDIA_ROOT is set to something temporary.
        self.original_media_root = django_settings.MEDIA_ROOT
        django_settings.MEDIA_ROOT = self.temp_media_dir_path


    def tearDown(self):
        django_settings.MEDIA_ROOT = self.original_media_root # Restore original MEDIA_ROOT
        self.temp_media_dir_obj.cleanup()
        self.zip_temp_dir_obj.cleanup()
        # Clean up any created Page, Attachment, ConfluenceUpload objects
        Page.objects.all().delete()
        Attachment.objects.all().delete()
        ConfluenceUpload.objects.all().delete()


    def _create_dummy_confluence_zip(self, zip_filename, html_files_data=None,
                                   attachment_files_data=None, create_attachments_subfolder=False,
                                   metadata_xml_content=None):
        html_files_data = html_files_data or {}; attachment_files_data = attachment_files_data or {}
        zip_file_path = os.path.join(self.zip_temp_dir_path, zip_filename)
        current_zip_content_dir = tempfile.mkdtemp(dir=self.zip_temp_dir_path)

        for name, content in html_files_data.items():
            file_path = os.path.join(current_zip_content_dir, name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f: f.write(content)

        attachments_root_in_zip = current_zip_content_dir
        if create_attachments_subfolder:
            attachments_root_in_zip = os.path.join(current_zip_content_dir, "attachments")
            os.makedirs(attachments_root_in_zip, exist_ok=True)

        for name, content in attachment_files_data.items():
            file_path = os.path.join(attachments_root_in_zip, name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True) # Ensure subdirs for attachments are created if path includes them
            with open(file_path, "wb") as f: f.write(content)

        if metadata_xml_content:
            metadata_filepath = os.path.join(current_zip_content_dir, "entities.xml")
            with open(metadata_filepath, "w", encoding="utf-8") as f: f.write(metadata_xml_content)

        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root_dir, _, files_in_dir in os.walk(current_zip_content_dir):
                for file_item in files_in_dir:
                    full_path = os.path.join(root_dir, file_item)
                    arcname = os.path.relpath(full_path, current_zip_content_dir)
                    zf.write(full_path, arcname)
        shutil.rmtree(current_zip_content_dir)
        return zip_file_path

    # Existing tests from previous phases (ensure self.space is used, which is self.space_default_in_ws_default now)
    def test_import_task_success_simple_page_no_attachments(self):
        if not self.space_default_in_ws_default: self.skipTest("Default Space not available.")
        html_data = {"p_123.html": "<html><title>T1</title><body><div id='main-content'><p>C1</p></div></body></html>"}
        metadata_xml = """<hibernate-generic><object class='Page'><property name='id'><long>123</long></property><property name='title'><string>T1</string></property></object></hibernate-generic>"""
        zip_path = self._create_dummy_confluence_zip("t1.zip", html_files_data=html_data, metadata_xml_content=metadata_xml)
        with open(zip_path, 'rb') as f: upload_file = SimpleUploadedFile(name="t1.zip",content=f.read(),content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file) # No target specified, uses fallback
        msg = import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        # Page should be in the default space used by fallback logic
        p = Page.objects.get(original_confluence_id="123", space=self.space_default_in_ws_default)
        self.assertEqual(p.title, "T1"); self.assertIn("C1", p.content_json['content'][0]['content'][0]['text'])
        self.assertEqual(Attachment.objects.count(), 0); self.assertIn("Pages created: 1", msg)

    def test_import_task_page_with_attachments_and_embedded_images(self):
        if not self.space_default_in_ws_default: self.skipTest("Default Space not available.")
        html_content = "<html><title>PAI</title><body><div id='main-content'><p><img src='../attachments/photo.png' alt='TP' title='MPT'> <img src='attachments/table_image.jpeg' alt='TI'></p></div></body></html>"
        html_data = {"p_img_800.html": html_content}
        attachments = {"photo.png": b"photo_data", "table_image.jpeg": b"jpeg_data"}
        metadata_xml = """<hibernate-generic><object class='Page'><property name='id'><long>800</long></property><property name='title'><string>PAI</string></property></object></hibernate-generic>"""
        zip_path = self._create_dummy_confluence_zip("t_img.zip", html_data, attachments, create_attachments_subfolder=True, metadata_xml_content=metadata_xml)
        with open(zip_path,'rb') as f: upload_file=SimpleUploadedFile("t_img.zip",f.read(),'application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file) # No target, uses fallback
        import_confluence_space(upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        page = Page.objects.get(original_confluence_id="800", space=self.space_default_in_ws_default) # Check in default space
        self.assertEqual(Attachment.objects.filter(page=page).count(), 2)
        # ... (rest of assertions for attachments and image src)

    def test_import_task_no_html_files_in_zip(self):
        # This test doesn't depend on space existence as it should fail early
        zip_path = self._create_dummy_confluence_zip("no_html.zip", metadata_xml_content="<hibernate-generic></hibernate-generic>") # Provide metadata so it doesn't fail for that reason
        with open(zip_path,'rb') as f: upload_file=SimpleUploadedFile("no_html.zip",f.read(),'application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        import_confluence_space(upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_FAILED)
        self.assertEqual(Page.objects.count(), 0)

    def test_import_task_with_page_hierarchy(self):
        if not self.space_default_in_ws_default: self.skipTest("Default Space not available for hierarchy test.")
        xml = "<hibernate-generic><object class='Page'><property name='id'><long>100</long></property><property name='title'><string>PH</string></property></object><object class='Page'><property name='id'><long>101</long></property><property name='title'><string>CH1</string></property><property name='parent'><id>100</id></property></object></hibernate-generic>"
        html = {"P_H_100.html":"<html><title>PH</title><body><p>P</p></body></html>", "C_H1_101.html":"<html><title>CH1</title><body><p>C</p></body></html>"}
        zip_path = self._create_dummy_confluence_zip("th.zip", html, metadata_xml_content=xml)
        with open(zip_path,'rb') as f: upload_file=SimpleUploadedFile("th.zip",f.read(),'application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file) # No target, uses fallback
        import_confluence_space(upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        self.assertEqual(Page.objects.count(), 2)
        p_h = Page.objects.get(original_confluence_id="100",space=self.space_default_in_ws_default) # Check in default space
        c_h1 = Page.objects.get(original_confluence_id="101",space=self.space_default_in_ws_default) # Check in default space
        self.assertEqual(c_h1.parent, p_h); self.assertIsNone(p_h.parent)
        self.assertIn(c_h1, p_h.children.all())

    def test_import_task_html_file_not_in_metadata_is_skipped(self):
        if not self.space_default_in_ws_default: self.skipTest("Default Space not available for testing.")
        sample_metadata_xml = """<hibernate-generic><object class="Page"><property name="id"><long>100</long></property><property name="title"><string>Page A Title from Meta</string></property></object></hibernate-generic>"""
        html_data = {"pageA_100.html": "<html><head><title>Page A Title from Meta</title></head><body>Content A</body></html>", "pageB_200.html": "<html><head><title>Page B Title (Not in Meta)</title></head><body>Content B</body></html>" }
        zip_path = self._create_dummy_confluence_zip("test_stray_html.zip", html_files_data=html_data, metadata_xml_content=sample_metadata_xml)
        upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=open(zip_path, 'rb').read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file) # Uses fallback
        result_message = import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        self.assertIn("Pages created: 1", result_message)
        self.assertEqual(Page.objects.count(), 1)
        self.assertTrue(Page.objects.filter(original_confluence_id="100", title="Page A Title from Meta", space=self.space_default_in_ws_default).exists())
        self.assertFalse(Page.objects.filter(title="Page B Title (Not in Meta)").exists())

    def test_import_task_page_in_metadata_html_title_mismatch(self):
        if not self.space_default_in_ws_default: self.skipTest("Default Space not available for testing.")
        sample_metadata_xml = """<hibernate-generic><object class="Page"><property name="id"><long>300</long></property><property name="title"><string>Title X from Meta</string></property></object></hibernate-generic>"""
        html_data = {"pageX_300.html": "<html><head><title>Different Title in HTML</title></head><body>Content X</body></html>"}
        zip_path = self._create_dummy_confluence_zip("test_title_mismatch.zip", html_files_data=html_data, metadata_xml_content=sample_metadata_xml)
        upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=open(zip_path, 'rb').read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file) # Uses fallback
        result_message = import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_FAILED)
        self.assertIn("Pages created: 0", result_message)
        self.assertEqual(Page.objects.count(), 0)

    def test_import_task_fails_if_metadata_file_is_present_but_empty_or_unparsable(self):
        if not self.space_default_in_ws_default: self.skipTest("Default Space not available for testing.")
        empty_metadata_xml = "<hibernate-generic></hibernate-generic>"
        html_data = {"page_data_400.html": "<html><head><title>Some Page</title></head><body>Content</body></html>"}
        zip_path_empty_meta = self._create_dummy_confluence_zip("test_empty_meta.zip", html_files_data=html_data, metadata_xml_content=empty_metadata_xml)
        upload_file_empty = SimpleUploadedFile(name=os.path.basename(zip_path_empty_meta), content=open(zip_path_empty_meta, 'rb').read(), content_type='application/zip')
        upload_record_empty = ConfluenceUpload.objects.create(user=self.user, file=upload_file_empty) # Uses fallback
        import_confluence_space(confluence_upload_id=upload_record_empty.id)
        upload_record_empty.refresh_from_db()
        self.assertEqual(upload_record_empty.status, ConfluenceUpload.STATUS_FAILED)
        Page.objects.all().delete(); ConfluenceUpload.objects.all().delete() # Cleanup for next case
        malformed_metadata_xml = "<unclosed><tag>"
        zip_path_malformed_meta = self._create_dummy_confluence_zip("test_malformed_meta.zip", html_files_data=html_data, metadata_xml_content=malformed_metadata_xml)
        upload_file_malformed = SimpleUploadedFile(name=os.path.basename(zip_path_malformed_meta), content=open(zip_path_malformed_meta, 'rb').read(), content_type='application/zip')
        upload_record_malformed = ConfluenceUpload.objects.create(user=self.user, file=upload_file_malformed) # Uses fallback
        import_confluence_space(confluence_upload_id=upload_record_malformed.id)
        upload_record_malformed.refresh_from_db()
        self.assertEqual(upload_record_malformed.status, ConfluenceUpload.STATUS_FAILED)

    # New tests for specific targeting
    def test_import_task_uses_explicit_target_space(self):
        if not self.ws_target or not self.space_target_in_ws_target:
            self.skipTest("Target Workspace/Space not available for this task test.")
        html_data = {"page_target_1.html": "<html><head><title>Targeted Page 1</title></head><body>Content</body></html>"}
        metadata_xml = """<hibernate-generic><object class="Page"><property name="id"><long>target1</long></property><property name="title"><string>Targeted Page 1</string></property></object></hibernate-generic>"""
        zip_path = self._create_dummy_confluence_zip("target_space_test.zip", html_files_data=html_data, metadata_xml_content=metadata_xml)
        upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=open(zip_path, 'rb').read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file, target_space=self.space_target_in_ws_target)
        import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        self.assertEqual(Page.objects.count(), 1)
        created_page = Page.objects.first()
        self.assertEqual(created_page.title, "Targeted Page 1")
        self.assertEqual(created_page.space, self.space_target_in_ws_target)
        self.assertEqual(created_page.space.workspace, self.ws_target) # Check inferred workspace

    def test_import_task_uses_explicit_target_workspace_finds_first_space(self):
        if not self.ws_target or not self.space_target_in_ws_target or not self.space_alt_in_ws_target:
            self.skipTest("Target Workspace/Spaces not available for this task test.")
        # To make test deterministic, ensure one space is clearly "first" or delete other spaces in this workspace
        # For this test, we'll rely on current task logic picking one of them.
        # If specific "first" space needs to be guaranteed, more setup (e.g. ordered by name/ID and picking one)
        # or cleaning up other spaces in ws_target would be needed.
        # self.space_alt_in_ws_target.delete() # Example: Ensure only space_target_in_ws_target exists

        html_data = {"page_target_ws_1.html": "<html><head><title>WS Targeted Page 1</title></head><body>Content</body></html>"}
        metadata_xml = """<hibernate-generic><object class="Page"><property name="id"><long>targetws1</long></property><property name="title"><string>WS Targeted Page 1</string></property></object></hibernate-generic>"""
        zip_path = self._create_dummy_confluence_zip("target_ws_test.zip", html_files_data=html_data, metadata_xml_content=metadata_xml)
        upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=open(zip_path, 'rb').read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file, target_workspace=self.ws_target)
        import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        created_page = Page.objects.get(original_confluence_id="targetws1")
        self.assertEqual(created_page.space.workspace, self.ws_target) # Must be in the target workspace
        self.assertIn(created_page.space, [self.space_target_in_ws_target, self.space_alt_in_ws_target]) # Belongs to one of the spaces in target WS

    def test_import_task_fallback_if_no_targets_set_on_upload(self):
        if not self.ws_default or not self.space_default_in_ws_default:
            self.skipTest("Default Workspace/Space not available for fallback test.")
        html_data = {"page_fallback_1.html": "<html><head><title>Fallback Page 1</title></head><body>Content</body></html>"}
        metadata_xml = """<hibernate-generic><object class="Page"><property name="id"><long>fallback1</long></property><property name="title"><string>Fallback Page 1</string></property></object></hibernate-generic>"""
        zip_path = self._create_dummy_confluence_zip("fallback_test.zip", html_files_data=html_data, metadata_xml_content=metadata_xml)
        upload_file = SimpleUploadedFile(name=os.path.basename(zip_path), content=open(zip_path, 'rb').read(), content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db()
        self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        created_page = Page.objects.get(original_confluence_id="fallback1")
        self.assertEqual(created_page.space, self.space_default_in_ws_default)
        self.assertEqual(created_page.space.workspace, self.ws_default)
