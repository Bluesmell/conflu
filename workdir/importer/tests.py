import os
import shutil
import tempfile
import zipfile
from django.test import TestCase
import textwrap # Keep for dummy HTML content formatting within tests
# Assuming utils.py and parser.py are in the same app 'importer'
from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic, parse_confluence_metadata_for_hierarchy # Added metadata parser
from .converter import convert_html_to_prosemirror_json # Function to test

# Added imports for ConfluenceImportViewTests
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

# Imports for updated tests and new model tests
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import ConfluenceUpload

# Imports for ConfluenceImportTaskTests
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
        cleanup_temp_extraction_dir(temp_extract_dir=self.extraction_target_dir)
        self.assertFalse(os.path.exists(self.extraction_target_dir))
    def test_extract_from_nonexistent_zip(self):
        html_files, metadata_file = extract_html_and_metadata_from_zip("nonexistent_utils.zip", temp_extract_dir=self.extraction_target_dir)
        self.assertEqual(len(html_files), 0)
        self.assertIsNone(metadata_file)
        self.assertFalse(os.path.exists(self.extraction_target_dir))
    def test_extract_from_bad_zip(self):
        bad_zip_path = os.path.join(self.base_temp_dir, "bad_utils.zip")
        with open(bad_zip_path, "w", encoding="utf-8") as f: f.write("this is not a zip file")
        html_files, metadata_file = extract_html_and_metadata_from_zip(bad_zip_path, temp_extract_dir=self.extraction_target_dir)
        self.assertEqual(len(html_files), 0)
        self.assertIsNone(metadata_file)
        self.assertFalse(os.path.exists(self.extraction_target_dir))

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

class ConfluenceImportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser_importer_view', password='password')
        self.client = APIClient(); self.client.force_authenticate(user=self.user)
        self.import_url = "/api/v1/io/import/confluence/"
    @patch('workdir.importer.views.import_confluence_space.delay')
    def test_post_request_triggers_import_task(self, mock_delay):
        dummy_file = SimpleUploadedFile("test.zip", b"content", "application/zip")
        response = self.client.post(self.import_url, {'file': dummy_file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(ConfluenceUpload.objects.count(), 1)
        upload = ConfluenceUpload.objects.first()
        mock_delay.assert_called_once_with(confluence_upload_id=upload.id)
        if upload.file: upload.file.delete(save=False)

class ConfluenceUploadModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testmodeluser', password='password')
        self.dummy_file = SimpleUploadedFile("model.zip", b"content", "application/zip")
    def tearDown(self):
        for upload in ConfluenceUpload.objects.all():
            if upload.file: upload.file.delete(save=False)
    def test_confluence_upload_creation(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)
        self.assertTrue(upload.file.name.endswith("model.zip"))
        self.assertEqual(upload.status, ConfluenceUpload.STATUS_PENDING)
    def test_confluence_upload_str_method(self):
        upload = ConfluenceUpload.objects.create(user=self.user, file=self.dummy_file)
        self.assertIn(str(upload.pk), str(upload))
        self.assertIn(self.user.username, str(upload))

class EnhancedHtmlParserTests(TestCase):
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
    def test_lists(self): # Checks current behavior for ul/ol/li direct text content
        self.assertEqual(convert_html_to_prosemirror_json("<ul><li>I1</li></ul>")['content'][0], {"type":"bullet_list","content":[{"type":"list_item","content":[{"type":"paragraph", "content":[{"type":"text","text":"I1"}]}]}]})
        self.assertEqual(convert_html_to_prosemirror_json("<ol><li>I1</li></ol>")['content'][0], {"type":"ordered_list","content":[{"type":"list_item","content":[{"type":"paragraph", "content":[{"type":"text","text":"I1"}]}]}]})
    def test_list_item_with_paragraph(self): # Checks li > p > text
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
        self.assertEqual(len(json_output['content'][0]['content']), 2) # Rows
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
        expected_json = {
            "type": "doc",
            "content": [{"type": "horizontal_rule"}]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_horizontal_rule_xml_self_closing(self): # e.g. <hr />
        html = "<hr />" # BeautifulSoup treats <hr> and <hr /> identically
        expected_json = {
            "type": "doc",
            "content": [{"type": "horizontal_rule"}]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_horizontal_rule_with_surrounding_paragraphs(self):
        html = "<p>Above</p><hr><p>Below</p>"
        expected_json = {
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Above"}]},
                {"type": "horizontal_rule"},
                {"type": "paragraph", "content": [{"type": "text", "text": "Below"}]}
            ]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_multiple_horizontal_rules(self):
        html = "<hr><hr/>" # Mixed style
        expected_json = {
            "type": "doc",
            "content": [
                {"type": "horizontal_rule"},
                {"type": "horizontal_rule"}
            ]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_simple_blockquote(self):
        html = "<blockquote><p>Quoted text here.</p></blockquote>"
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Quoted text here."}]
                }]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_with_multiple_paragraphs(self):
        html = "<blockquote><p>First para.</p><p>Second para.</p></blockquote>"
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "First para."}]},
                    {"type": "paragraph", "content": [{"type": "text", "text": "Second para."}]}
                ]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_empty_blockquote(self):
        html = "<blockquote></blockquote>"
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "content": [{"type": "paragraph", "content": []}]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_with_inline_marks_in_paragraph(self):
        html = "<blockquote><p>Quote with <strong>bold</strong> text.</p></blockquote>"
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "content": [{
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "Quote with "},
                        {"type": "text", "marks": [{"type": "bold"}], "text": "bold"},
                        {"type": "text", "text": " text."}
                    ]
                }]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_blockquote_with_direct_text_content_is_wrapped(self):
        html = "<blockquote>This text is directly in the blockquote.</blockquote>"
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "This text is directly in the blockquote."}]
                }]
            }]
        }
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
        html = """
        <div class="confluence-information-macro confluence-information-macro-information">
            <div class="confluence-information-macro-body"><p>This is an info panel.</p></div>
        </div>
        """
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "attrs": {"panelType": "info"},
                "content": [{
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "This is an info panel."}]
                }]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_confluence_note_panel_with_direct_text(self):
        html = """
        <div class="confluence-information-macro confluence-information-macro-note">
            <div class="confluence-information-macro-body">Note text here.</div>
        </div>
        """
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "attrs": {"panelType": "note"},
                "content": [{ # Direct text in body should be wrapped in a paragraph
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "Note text here."}]
                }]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_confluence_warning_panel_with_list(self):
        html = """
        <div class="confluence-information-macro confluence-information-macro-warning">
            <div class="confluence-information-macro-body">
                <ul><li>Warning item 1</li></ul>
            </div>
        </div>
        """
        json_output = convert_html_to_prosemirror_json(html)
        self.assertEqual(json_output['type'], 'doc')
        panel_node = json_output['content'][0]
        self.assertEqual(panel_node['type'], 'blockquote')
        self.assertEqual(panel_node.get('attrs', {}).get('panelType'), 'warning')

        # If the only child of the panel body is a block (like a list), it should be preserved as such.
        self.assertTrue(len(panel_node['content']) > 0, "Panel content should not be empty")
        list_node = panel_node['content'][0]
        self.assertEqual(list_node['type'], 'bullet_list')
        self.assertEqual(list_node['content'][0]['content'][0]['content'][0]['text'], 'Warning item 1')

    def test_confluence_tip_panel_empty_body(self):
        html = """
        <div class="confluence-information-macro confluence-information-macro-tip">
            <div class="confluence-information-macro-body"></div>
        </div>
        """
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "blockquote",
                "attrs": {"panelType": "tip"},
                "content": [{"type": "paragraph", "content": []}] # Empty body -> empty paragraph
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_panel_div_only_base_class_is_unwrapped(self):
        # Test a div that has "confluence-information-macro" but not a specific type like "-note"
        html = """
        <div class="confluence-information-macro">
            <p>Content of a generic panel-like div.</p>
        </div>
        """
        # Current logic: if panel_type is None (no specific suffix like "-info"), it's not treated as a panel.
        # It will then fall through to default div handling (which is unwrap).
        expected_json = {
            "type": "doc",
            "content": [{
                "type": "paragraph",
                "content": [{"type": "text", "text": "Content of a generic panel-like div."}]
            }]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

    def test_panel_with_title_div_is_ignored(self):
        html = """
        <div class="confluence-information-macro confluence-information-macro-note">
            <div class="confluence-information-macro-title">This is a Title</div>
            <div class="confluence-information-macro-body">
                <p>Actual content.</p>
            </div>
        </div>
        """
        expected_json = {
            "type": "doc", "content": [
                {"type": "blockquote", "attrs": {"panelType": "note"}, "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Actual content."}]}
                ]}
            ]
        }
        self.assertEqual(convert_html_to_prosemirror_json(html), expected_json)

from .parser import parse_confluence_metadata_for_hierarchy # This is the correct, first instance

class ConfluenceMetadataParserTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="metadata_parser_tests_")
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
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
    def test_parse_file_not_found(self):
        self.assertEqual(parse_confluence_metadata_for_hierarchy("n.xml"), [])
    def test_parse_malformed_xml(self):
        self.assertEqual(parse_confluence_metadata_for_hierarchy(self._create_dummy_xml_file("m.xml", "<u")), [])

# Imports for ConfluenceImportTaskTests
from django.conf import settings as django_settings
from django.test import override_settings
from .tasks import import_confluence_space
from pages.models import Page, Attachment
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
            if Space and cls.workspace :
                cls.space = Space.objects.create(name='Task Test Space', workspace=cls.workspace)
            else: cls.space = None
        else: cls.workspace = None; cls.space = None
        if not cls.workspace or not cls.space: print("ConfluenceImportTaskTests: Workspace/Space models not available. Some tests might be skipped.")
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
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
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
        shutil.rmtree(current_zip_content_dir); return zip_file_path

    def test_import_task_success_simple_page_no_attachments(self):
        if not self.space: self.skipTest("Space not available.")
        html_data = {"p_123.html": "<html><title>T1</title><body><div id='main-content'><p>C1</p></div></body></html>"}
        zip_path = self._create_dummy_confluence_zip("t1.zip", html_files_data=html_data)
        with open(zip_path, 'rb') as f: upload_file = SimpleUploadedFile(name="t1.zip",content=f.read(),content_type='application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        msg = import_confluence_space(confluence_upload_id=upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        p = Page.objects.get(original_confluence_id="123", space=self.space)
        self.assertEqual(p.title, "T1"); self.assertIn("C1", p.content_json['content'][0]['content'][0]['text'])
        self.assertEqual(Attachment.objects.count(), 0); self.assertIn("Pages created: 1", msg)

    def test_import_task_page_with_attachments_and_embedded_images(self):
        if not self.space: self.skipTest("Space not available.")
        html_content = "<html><title>PAI</title><body><div id='main-content'><p><img src='../attachments/photo.png' alt='TP' title='MPT'> <img src='attachments/table_image.jpeg' alt='TI'></p></div></body></html>"
        html_data = {"p_img_800.html": html_content}
        attachments = {"photo.png": b"photo_data", "table_image.jpeg": b"jpeg_data"}
        zip_path = self._create_dummy_confluence_zip("t_img.zip", html_data, attachments, create_attachments_subfolder=True)
        with open(zip_path,'rb') as f: upload_file=SimpleUploadedFile("t_img.zip",f.read(),'application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        import_confluence_space(upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        page = Page.objects.get(original_confluence_id="800", space=self.space)
        self.assertEqual(Attachment.objects.filter(page=page).count(), 2)
        photo = Attachment.objects.get(page=page, original_filename="photo.png")
        table_img = Attachment.objects.get(page=page, original_filename="table_image.jpeg")

        found_srcs = []
        def find_img_srcs(nodes):
            for n in nodes:
                if n.get("type")=="image": found_srcs.append(n.get("attrs",{}).get("src"))
                if "content" in n and isinstance(n["content"],list): find_img_srcs(n["content"])
        if page.content_json and 'content' in page.content_json: find_img_srcs(page.content_json['content'])

        self.assertIn(photo.file.url, found_srcs)
        self.assertIn(table_img.file.url, found_srcs)
        # Check for alt/title on one image
        for n in page.content_json['content'][0]['content']: # Assuming first paragraph, first image
            if n.get("type") == "image" and n['attrs']['src'] == photo.file.url:
                self.assertEqual(n['attrs']['alt'], 'TP'); self.assertEqual(n['attrs']['title'], 'MPT'); break
        else: self.fail("Primary image node not found or attrs incorrect")

    def test_import_task_no_html_files_in_zip(self):
        zip_path = self._create_dummy_confluence_zip("no_html.zip", attachment_files_data={"t.txt":b"d"})
        with open(zip_path,'rb') as f: upload_file=SimpleUploadedFile("no_html.zip",f.read(),'application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        import_confluence_space(upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_FAILED)
        self.assertEqual(Page.objects.count(), 0)

    def test_import_task_with_page_hierarchy(self):
        if not self.space: self.skipTest("Space not available for hierarchy test.")
        xml = "<hibernate-generic><object class='Page'><property name='id'><long>100</long></property><property name='title'><string>P H</string></property></object><object class='Page'><property name='id'><long>101</long></property><property name='title'><string>C H1</string></property><property name='parent'><id>100</id></property></object></hibernate-generic>"
        html = {"P_H_100.html":"<html><title>PH</title><body><p>P</p></body></html>", "C_H1_101.html":"<html><title>CH1</title><body><p>C</p></body></html>"}
        zip_path = self._create_dummy_confluence_zip("th.zip", html, metadata_xml_content=xml)
        with open(zip_path,'rb') as f: upload_file=SimpleUploadedFile("th.zip",f.read(),'application/zip')
        upload_record = ConfluenceUpload.objects.create(user=self.user, file=upload_file)
        import_confluence_space(upload_record.id)
        upload_record.refresh_from_db(); self.assertEqual(upload_record.status, ConfluenceUpload.STATUS_COMPLETED)
        self.assertEqual(Page.objects.count(), 2)
        p_h = Page.objects.get(original_confluence_id="100",space=self.space)
        c_h1 = Page.objects.get(original_confluence_id="101",space=self.space)
        self.assertEqual(c_h1.parent, p_h); self.assertIsNone(p_h.parent)
        self.assertIn(c_h1, p_h.children.all())
