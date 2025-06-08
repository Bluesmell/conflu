from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import unquote
import os
import json # For __main__ block pretty printing
import re # For parsing language from class attributes

def map_tag_to_prosemirror_type(tag_name, node=None): # Added node for class inspection
    """Maps HTML tag names to ProseMirror node or mark types."""
    base_mapping = {
        'p': 'paragraph', 'br': 'hard_break',
        'h1': 'heading', 'h2': 'heading', 'h3': 'heading',
        'h4': 'heading', 'h5': 'heading', 'h6': 'heading',
        'table': 'table', 'tr': 'table_row', 'th': 'table_header', 'td': 'table_cell',
        'pre': 'code_block',
        'blockquote': 'blockquote',
        'hr': 'horizontal_rule', # Added for horizontal rules
    }

    if tag_name == 'ul':
        if isinstance(node, Tag) and 'task-list' in node.get('class', []):
            return 'task_list'
        return 'bullet_list'
    if tag_name == 'ol':
        return 'ordered_list'
    if tag_name == 'li':
        if isinstance(node, Tag) and 'task-list-item' in node.get('class', []):
            return 'task_item'
        # Contextual check (e.g., parent_pm_type == 'task_list') will be handled in process_node
        return 'list_item'

    return base_mapping.get(tag_name, None)

def get_heading_attrs(tag_name):
    """Returns attributes for a heading node, like level."""
    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        return {'level': int(tag_name[1])}
    return {}

def process_node(node, current_marks=None, parent_pm_type=None):
    if current_marks is None: current_marks = []

    if isinstance(node, NavigableString):
        text_content = str(node)
        if parent_pm_type != 'code_block' and not text_content.strip(): return []
        fragment = {"type": "text", "text": text_content}
        if current_marks and parent_pm_type != 'code_block':
            fragment["marks"] = current_marks[:]
        return [fragment]

    elif isinstance(node, Tag):
        if node.name == 'img':
            attrs = {}
            original_src = node.get('src')
            if not original_src: return []
            symbolic_filename = os.path.basename(unquote(original_src.split('?')[0]))
            attrs['src'] = f"pm:attachment:{symbolic_filename}"
            if node.get('alt') is not None: attrs['alt'] = node.get('alt')
            if node.get('title') is not None: attrs['title'] = node.get('title')
            return [{"type": "image", "attrs": attrs}]
        elif node.name == 'hr': # Handle hr as a specific void block
            return [{"type": "horizontal_rule"}]
        # Removed 'br' from here as it's better handled by map_tag_to_prosemirror_type and default block logic

        # Confluence Panel Div Check
        if node.name == 'div' and node.has_attr('class'):
            node_classes = node.get('class', [])
            panel_type = None
            base_class = "confluence-information-macro"

            # Determine panel type from class names
            if base_class in node_classes:
                for cls in node_classes:
                    if cls.startswith(base_class + "-") and cls != base_class:
                        panel_type_candidate = cls.replace(base_class + "-", "", 1)
                        # Normalize common panel types, allow others through
                        if panel_type_candidate == "information": panel_type = "info"
                        elif panel_type_candidate == "warning": panel_type = "warning"
                        elif panel_type_candidate == "note": panel_type = "note"
                        elif panel_type_candidate == "tip": panel_type = "tip"
                        else: panel_type = panel_type_candidate # Use as is if not a standard one
                        break

            if panel_type:
                panel_child_content_collected = []
                # Prioritize content from '.confluence-information-macro-body'
                content_body_div = node.find('div', class_='confluence-information-macro-body')
                target_content_node_for_panel = content_body_div if content_body_div else node

                for child in target_content_node_for_panel.children:
                    # Skip title divs if they exist within the panel's content scope
                    if isinstance(child, Tag) and 'confluence-information-macro-title' in child.get('class', []):
                        continue
                    # Process children with reset marks, 'blockquote' context for content normalization
                    panel_child_content_collected.extend(process_node(child, [], 'blockquote'))

                # Normalize panel content: ensure it's block-level
                processed_panel_content = []
                if not panel_child_content_collected:
                    processed_panel_content.append({"type": "paragraph", "content": []})
                else:
                    # Group consecutive inline items and wrap them in a paragraph.
                    # Block items are added directly.
                    inline_buffer = []
                    for item in panel_child_content_collected:
                        item_type = item.get("type")
                        if item_type in ["text", "hard_break", "image"] or item.get("marks"): # Inline types
                            if item_type == "text" and not item.get("text", "").strip() and not inline_buffer: # Skip leading/isolated whitespace
                                continue
                            inline_buffer.append(item)
                        else: # Block type
                            if inline_buffer:
                                processed_panel_content.append({"type": "paragraph", "content": inline_buffer})
                                inline_buffer = []
                            processed_panel_content.append(item)
                    if inline_buffer: # Append any remaining inlines
                        processed_panel_content.append({"type": "paragraph", "content": inline_buffer})

                    # If after processing, content is empty (e.g. only contained empty paragraphs that got stripped), add one empty paragraph
                    if not processed_panel_content:
                         processed_panel_content.append({"type": "paragraph", "content": []})


                return [{
                    "type": "blockquote", # Using blockquote as the base node for panels
                    "attrs": {"panelType": panel_type},
                    "content": processed_panel_content
                }]

        node_type = map_tag_to_prosemirror_type(node.name, node)
        if node.name == 'li' and parent_pm_type == 'task_list': # Contextual check for task_item
            node_type = 'task_item'

        if node_type == 'code_block':
            code_content = node.get_text()
            pm_node_content = [{"type": "text", "text": code_content}] if code_content else [{"type": "text", "text": ""}]
            attrs = {}
            lang = None # Initialize lang

            if node.has_attr('class'):
                class_list = node['class']

                # Try standard prefixes first
                for cn_item in class_list:
                    if cn_item.startswith('language-'):
                        lang = cn_item.replace('language-', '', 1)
                        break
                    if cn_item.startswith('lang-'):
                        lang = cn_item.replace('lang-', '', 1)
                        break

                # If not found by prefix, try the refined 'brush:' logic
                if not lang:
                    try:
                        idx_of_brush_marker = -1
                        class_containing_brush_prefix = None
                        for idx, cn_item in enumerate(class_list):
                            if cn_item.startswith('brush:'):
                                idx_of_brush_marker = idx
                                class_containing_brush_prefix = cn_item
                                break

                        if idx_of_brush_marker != -1: # Found an item starting with 'brush:'
                            if class_containing_brush_prefix == 'brush:' and idx_of_brush_marker + 1 < len(class_list):
                                # Case: class_list = ['brush:', 'java;', ...]
                                potential_lang_token = class_list[idx_of_brush_marker + 1]
                                lang = potential_lang_token.rstrip('; ')
                            else:
                                # Case: class_list = ['brush:java;', ...] or ['brush:java', ...]
                                potential_lang_token = class_containing_brush_prefix.replace('brush:', '', 1).strip()
                                # If language is part of a parameter string like "java; gutter: false", split it.
                                if ';' in potential_lang_token:
                                    lang = potential_lang_token.split(';')[0].strip()
                                else:
                                    lang = potential_lang_token

                            # Further clean common syntax if they are part of lang string by mistake
                            if lang and lang.lower() in ['true', 'false', 'gutter', 'toolbar']:
                                lang = None # This was likely not a language

                    except Exception:
                        lang = None # Ensure lang is None if parsing fails

            if lang:
                attrs['language'] = lang.lower()
            pm_node = {"type": "code_block", "content": pm_node_content}
            if attrs: pm_node['attrs'] = attrs
            return [pm_node]

        new_marks = current_marks[:]
        mark_type_name, mark_attrs = None, {}
        if node.name in ['strong', 'b']: mark_type_name = 'bold'
        elif node.name in ['em', 'i']: mark_type_name = 'italic'
        elif node.name == 'a' and node.has_attr('href'):
            mark_type_name = 'link'; mark_attrs = {"href": node['href']}

        if mark_type_name:
            is_active = any(m['type'] == mark_type_name and (mark_type_name != 'link' or m.get('attrs') == mark_attrs) for m in new_marks)
            if not is_active:
                mark_to_add = {"type": mark_type_name}
                if mark_attrs: mark_to_add["attrs"] = mark_attrs
                new_marks.append(mark_to_add)

        child_marks_context = new_marks
        if node_type in ['table', 'table_row', 'table_header', 'table_cell',
                         'bullet_list', 'ordered_list', 'task_list', 'list_item', 'task_item',
                         'blockquote', 'code_block']:
            child_marks_context = []

        child_content = []
        # child_processing_parent_type context is node_type (if it's a block that defines context like list or blockquote)
        # or inherits from the current parent_pm_type.
        child_processing_parent_type = node_type if node_type in ['task_list', 'bullet_list', 'ordered_list', 'blockquote'] else parent_pm_type

        if node.name not in ['pre']: # <pre> content handled by get_text() for code_block
            if node.name == 'table':
                for child_group in node.children:
                    if isinstance(child_group, Tag):
                        if child_group.name in ['thead', 'tbody', 'tfoot']:
                            for child_row in child_group.children:
                                if isinstance(child_row, Tag) and child_row.name == 'tr':
                                    child_content.extend(process_node(child_row, [], child_processing_parent_type))
                        elif child_group.name == 'tr':
                            child_content.extend(process_node(child_group, [], child_processing_parent_type))
            elif node.name == 'tr':
                for child_cell in node.children:
                    if isinstance(child_cell, Tag) and child_cell.name in ['th', 'td']:
                        child_content.extend(process_node(child_cell, [], child_processing_parent_type))
            elif node_type == 'task_item':
                task_body_span = node.find('span', class_='task-item-body')
                target_node_for_task_content = task_body_span if task_body_span else node
                for child in target_node_for_task_content.children:
                    child_content.extend(process_node(child, child_marks_context, child_processing_parent_type))
            else:
                for child in node.children:
                    child_content.extend(process_node(child, child_marks_context, child_processing_parent_type))

        # Post-process content for specific block types (cells, list items, task items, blockquotes)
        if node_type in ['table_header', 'table_cell', 'list_item', 'task_item', 'blockquote']:
            processed_block_content = []
            if not child_content: # If there's no content at all (e.g. empty <td></td> or <li></li>)
                 if node_type not in ['task_item']: # Task item can be genuinely empty of text content
                    processed_block_content.append({"type": "paragraph", "content": []})
                 # else for task_item, empty child_content is fine
            else:
                # Check if all children are inline. If so, wrap them in a paragraph.
                is_any_child_block = any(item.get('type') not in ['text', 'hard_break', 'image'] for item in child_content)
                if not is_any_child_block: # All children are inline
                    meaningful_content = [item for item in child_content if not (item.get('type') == 'text' and not item.get('text','').strip())]
                    if meaningful_content or node_type not in ['task_item']:
                        processed_block_content.append({"type": "paragraph", "content": meaningful_content})
                    # If task_item and meaningful_content is empty, it means child_content was only whitespace.
                else: # Contains one or more block children already
                    processed_block_content = child_content
            child_content = processed_block_content

            if node_type == 'task_item' and child_content == [{"type":"paragraph","content":[]}]:
                child_content = [] # Task items can have no content if they are just a checkbox state
            elif not child_content and node_type in ['table_header', 'table_cell', 'list_item', 'blockquote']:
                 child_content = [{"type": "paragraph", "content": []}] # These must contain a paragraph

        if not child_content and node.name not in ['br', 'img', 'hr'] and \
           node_type not in ['table_header', 'table_cell', 'paragraph', 'heading', 'list_item', 'task_item', 'code_block', 'blockquote', 'horizontal_rule']:
            return []

        if node_type:
            pm_node = {"type": node_type}
            # Ensure content key is present for types that expect it, unless it's a contentless node like horizontal_rule or hard_break
            if node_type not in ['horizontal_rule', 'hard_break']:
                if child_content is not None or node_type in ['paragraph', 'heading', 'list_item', 'task_item',
                                                'bullet_list', 'ordered_list', 'task_list', 'blockquote',
                                                'table', 'table_row', 'table_header', 'table_cell', 'code_block']:
                    pm_node["content"] = child_content if child_content is not None else []

            attrs = {}
            if node_type == 'heading': attrs.update(get_heading_attrs(node.name))
            if node_type in ['table_header', 'table_cell']:
                for attr_name in ['colspan', 'rowspan']:
                    if node.has_attr(attr_name):
                        try:
                            val = int(node[attr_name])
                            if val > 1: attrs[attr_name] = val
                        except ValueError: pass
            if node_type == 'task_item':
                is_checked = node.get('data-task-status') == 'complete'
                if not node.get('data-task-status'): # Fallback for simple <input type=checkbox checked>
                    checkbox = node.find('input', type='checkbox')
                    if checkbox and checkbox.has_attr('checked'): is_checked = True
                attrs['checked'] = is_checked

            if attrs: pm_node["attrs"] = attrs
            return [pm_node]

        elif mark_type_name: return child_content
        elif node.name in ['thead', 'tbody', 'tfoot']: return child_content # Handled by table
        else: return child_content # Unwrap unmapped tags

    return []

def convert_html_to_prosemirror_json(html_string):
    if not html_string: return {"type": "doc", "content": []}
    soup = BeautifulSoup(html_string, 'lxml')
    parse_target = soup.body if soup.body else soup
    doc_content = []
    for element in parse_target.children:
        processed_elements = process_node(element, parent_pm_type=None)
        doc_content.extend(processed_elements)

    final_doc_content = []
    for item in doc_content:
        if item.get("type") in ["text", "hard_break", "image"] or item.get("marks"): # Inline nodes at top level
            if item.get("type") == "text" and not item.get("text", "").strip(): continue # Skip pure whitespace
            final_doc_content.append({"type": "paragraph", "content": [item]})
        elif item.get("type"): # Already a valid block node
            final_doc_content.append(item)
    return {"type": "doc", "content": final_doc_content}

if __name__ == '__main__':
    # This main block is for demonstration.
    # It's recommended to keep existing examples and add new ones.
    # For brevity, only new/relevant examples might be shown in planning.
    print("Testing HTML to ProseMirror JSON Converter...")

    # Example __main__ content from Turn 49 (Task List & Code Block)
    # (Assuming this overwrite intends to CUMULATIVELY add features)
    # Retain previous examples (p, h1, lists, links, tables, images) implicitly.

    print("\n--- Testing Task List Conversion ---")
    sample_html_task_list = """
    <ul class="task-list">
      <li class="task-list-item" data-task-id="1" data-task-status="complete"><span class="task-item-body">Completed task</span></li>
      <li class="task-list-item" data-task-id="2" data-task-status="incomplete"><span class="task-item-body">Open task with <strong>style</strong></span></li>
    </ul>
    """
    json_output_tasks = convert_html_to_prosemirror_json(sample_html_task_list)
    print("JSON Output Task List:", json.dumps(json_output_tasks, indent=2))

    print("\n--- Testing Code Block Conversion ---")
    sample_html_pre = '<pre class="language-python">def hello():\n  print("Hello")</pre>'
    json_output_pre = convert_html_to_prosemirror_json(sample_html_pre)
    print("JSON Output Code Block:", json.dumps(json_output_pre, indent=2))

    print("\n--- Testing Blockquote Conversion ---")
    sample_html_blockquote = "<blockquote><p>This is a quote.</p><p>Another paragraph in quote.</p></blockquote>"
    json_output_blockquote = convert_html_to_prosemirror_json(sample_html_blockquote)
    print("JSON Output Blockquote:", json.dumps(json_output_blockquote, indent=2))

    sample_html_blockquote_plain_text = "<blockquote>Just quoted text. Not in a p.</blockquote>"
    json_output_blockquote_plain = convert_html_to_prosemirror_json(sample_html_blockquote_plain_text)
    print("JSON Output Blockquote Plain Text:", json.dumps(json_output_blockquote_plain, indent=2))

    print("\n--- Testing Confluence Panel Conversion ---")
    sample_html_panel = """
    <div class="confluence-information-macro confluence-information-macro-information">
        <div class="confluence-information-macro-title">Info Title</div>
        <span class="aui-icon aui-icon-small aui-iconfont-info confluence-information-macro-icon"></span>
        <div class="confluence-information-macro-body">
            <p>This is an info panel.</p>
            <ul><li>With a list item.</li></ul>
        </div>
    </div>
    <div class="confluence-information-macro confluence-information-macro-note">
        <div class="confluence-information-macro-body">Just text in a note.</div>
    </div>
    """
    json_output_panel = convert_html_to_prosemirror_json(sample_html_panel)
    print("\nSample Panel HTML:", sample_html_panel)
    print("JSON Output Panel:", json.dumps(json_output_panel, indent=2))
