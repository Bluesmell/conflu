from bs4 import BeautifulSoup, NavigableString, Tag
from urllib.parse import unquote # For img src processing
import os # For img src processing (os.path.basename)
import json # For __main__ block pretty printing

def map_tag_to_prosemirror_type(tag_name):
    """Maps HTML tag names to ProseMirror node or mark types."""
    # Existing mappings:
    base_mapping = {
        'p': 'paragraph', 'br': 'hard_break',
        'h1': 'heading', 'h2': 'heading', 'h3': 'heading',
        'h4': 'heading', 'h5': 'heading', 'h6': 'heading',
        'table': 'table', 'tr': 'table_row', 'th': 'table_header', 'td': 'table_cell',
    }
    # Handle lists and task lists based on class for <ul> or context for <li>
    if tag_name == 'ul':
        # Check if node is a Tag instance before accessing get method for class
        if isinstance(node, Tag) and 'task-list' in node.get('class', []):
            return 'task_list'
        return 'bullet_list'
    if tag_name == 'ol':
        return 'ordered_list'
    if tag_name == 'li':
        # A more robust way is to check parent type in process_node.
        # For now, map based on class if present, otherwise default to list_item.
        if isinstance(node, Tag) and 'task-list-item' in node.get('class', []):
            return 'task_item'
        return 'list_item'

    return base_mapping.get(tag_name, None)

def get_heading_attrs(tag_name):
    """Returns attributes for a heading node, like level."""
    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        return {'level': int(tag_name[1])}
    return {}

def process_node(node, current_marks=None, parent_pm_type=None): # Added parent_pm_type
    """
    Recursively processes a BeautifulSoup node and its children
    to generate ProseMirror JSON fragments.
    """
    if current_marks is None:
        current_marks = []

    content_fragments = []

    if isinstance(node, NavigableString):
        text_content = str(node)
        if not text_content.strip(): # Skip nodes that are purely whitespace
            return []

        fragment = {"type": "text", "text": text_content}
        if current_marks:
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

        node_type = map_tag_to_prosemirror_type(node.name, node) # Pass node for class checking

        # Determine if current <li> should be a task_item based on parent_pm_type
        if node.name == 'li' and parent_pm_type == 'task_list':
            node_type = 'task_item'

        new_marks = current_marks[:]
        mark_type_name = None
        mark_attrs = {}
        if node.name in ['strong', 'b']: mark_type_name = 'bold'
        elif node.name in ['em', 'i']: mark_type_name = 'italic'
        if node.name == 'a' and node.has_attr('href'):
            mark_type_name = 'link'
            mark_attrs = {"href": node['href']}

        if mark_type_name:
            is_active = any(
                m['type'] == mark_type_name and (mark_type_name != 'link' or m.get('attrs') == mark_attrs)
                for m in new_marks
            )
            if not is_active:
                mark_to_add = {"type": mark_type_name}
                if mark_attrs:
                    mark_to_add["attrs"] = mark_attrs
                new_marks.append(mark_to_add)

        child_content = []
        # Determine child processing context (pass current node_type if it's a list type)
        child_processing_parent_type = node_type if node_type in ['task_list', 'bullet_list', 'ordered_list'] else parent_pm_type

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
        elif node_type == 'task_item': # Special content extraction for task_item
            task_body_span = node.find('span', class_='task-item-body')
            target_node_for_task_content = task_body_span if task_body_span else node
            for child in target_node_for_task_content.children:
                child_content.extend(process_node(child, new_marks, child_processing_parent_type))
        else:
            for child in node.children:
                child_content.extend(process_node(child, new_marks, child_processing_parent_type))

        # Post-process content for cells, list_items, and task_items
        if node_type in ['table_header', 'table_cell', 'list_item', 'task_item']:
            processed_block_item_content = []
            if not child_content:
                 # Task items can be legitimately empty if just a checkbox state, others need a paragraph
                 if node_type not in ['task_item']:
                    processed_block_item_content.append({"type": "paragraph", "content": []})
            else:
                is_block_content_present = any(item.get('type') not in ['text', 'hard_break', 'image'] for item in child_content)
                if not is_block_content_present:
                    meaningful_content = [item for item in child_content if not (item.get('type') == 'text' and not item.get('text','').strip())]
                    if meaningful_content or node_type not in ['task_item']: # Task item can be empty paragraph
                        processed_block_item_content.append({"type": "paragraph", "content": meaningful_content})
                    # if task_item is empty after this, it means it truly has no text body.
                else:
                    processed_block_item_content = child_content
            child_content = processed_block_item_content
            # If task_item's content became an empty paragraph list, make it an empty list for PM schema
            if node_type == 'task_item' and child_content == [{"type": "paragraph", "content": []}] :
                # Some schemas might prefer no content array vs. paragraph with no content for task_item text body
                # For now, let's keep the empty paragraph for consistency with list_item.
                pass


        if not child_content and node.name not in ['br', 'img'] and \
           node_type not in ['table_header', 'table_cell', 'paragraph', 'heading', 'list_item', 'task_item']:
            return []

        if node_type:
            pm_node = {"type": node_type}
            if child_content or node_type in ['paragraph', 'heading', 'list_item', 'task_item',
                                             'bullet_list', 'ordered_list', 'task_list',
                                             'table', 'table_row', 'table_header', 'table_cell']:
                pm_node["content"] = child_content if child_content is not None else [] # Ensure content is at least []

            attrs = {}
            if node_type == 'heading': attrs.update(get_heading_attrs(node.name))
            if node_type in ['table_header', 'table_cell']:
                if node.has_attr('colspan'):
                    try:
                        val = int(node['colspan'])
                        if val > 1: attrs['colspan'] = val # Only add if > 1
                    except ValueError: pass
                if node.has_attr('rowspan'):
                    try:
                        val = int(node['rowspan'])
                        if val > 1: attrs['rowspan'] = val # Only add if > 1
                    except ValueError: pass

            if attrs:
                pm_node["attrs"] = attrs

            return [pm_node]

        elif mark_type_name:
            return child_content

        else:
            # print(f"Warning: Unmapped tag <{node.name}>, processing children directly (unwrapping).")
            return child_content

    return content_fragments


def convert_html_to_prosemirror_json(html_string):
    """
    Converts an HTML string into a ProseMirror compatible JSON structure.
    """
    if not html_string:
        return {"type": "doc", "content": []}

    soup = BeautifulSoup(html_string, 'lxml')
    parse_target = soup.body if soup.body else soup

    doc_content = []
    for element in parse_target.children:
        processed_elements = process_node(element)
        doc_content.extend(processed_elements)

    final_doc_content = []
    for item in doc_content:
        # Basic cleanup: If a paragraph node contains only whitespace text, remove it or make it empty.
        # This is a common scenario after stripping other tags.
        if item.get("type") == "paragraph" and item.get("content"):
            is_empty_paragraph = True
            for content_node in item["content"]:
                if content_node.get("type") == "text" and content_node.get("text").strip() == "":
                    continue # This text node is effectively empty
                elif content_node.get("type") == "text" and content_node.get("text").strip() != "":
                    is_empty_paragraph = False # Found non-empty text
                    break
                else: # Found other non-text node like hard_break
                    is_empty_paragraph = False
                    break
            if is_empty_paragraph:
                # Either skip this paragraph or ensure its content is truly empty list
                # For now, let's ensure its content is empty if it was all whitespace text
                item["content"] = [c for c in item["content"] if c.get("type") != "text" or c.get("text").strip() != ""]
                if not item["content"]: continue # Skip if paragraph becomes truly empty

        # Wrap top-level text nodes in paragraphs
        if item.get("type") == "text":
            # If text is just whitespace, skip it at top level
            if item.get("text", "").strip():
                final_doc_content.append({"type": "paragraph", "content": [item]})
        else:
            final_doc_content.append(item)

    return {"type": "doc", "content": final_doc_content}

if __name__ == '__main__':
    print("Testing HTML to ProseMirror JSON Converter...")

    sample_html_1 = "<p>Hello <strong>bold world</strong><em>italic text</em></p>"
    json_output_1 = convert_html_to_prosemirror_json(sample_html_1)
    print("\nSample 1 HTML:", sample_html_1)
    print("JSON Output 1:", json_output_1)

    sample_html_2 = "<h1>Main Heading</h1><p>Some text here.<br>New line.</p>"
    json_output_2 = convert_html_to_prosemirror_json(sample_html_2)
    print("\nSample 2 HTML:", sample_html_2)
    print("JSON Output 2:", json_output_2)

    sample_html_3 = "<ul><li>Item 1</li><li>Item 2 with <b>bold</b></li></ul><ol><li>First</li></ol>"
    json_output_3 = convert_html_to_prosemirror_json(sample_html_3)
    print("\nSample 3 HTML:", sample_html_3)
    print("JSON Output 3:", json_output_3)

    sample_html_4 = '<p><a href="http://example.com">Example Link</a> and some <strong><em>bold italic</em></strong> text.</p>'
    json_output_4 = convert_html_to_prosemirror_json(sample_html_4)
    print("\nSample 4 HTML:", sample_html_4)
    print("JSON Output 4:", json_output_4)

    sample_html_5 = "Just some loose text. And more."
    json_output_5 = convert_html_to_prosemirror_json(sample_html_5)
    print("\nSample 5 HTML:", sample_html_5)
    print("JSON Output 5:", json_output_5)

    sample_html_6 = "<div><p>Paragraph inside a div</p></div>"
    json_output_6 = convert_html_to_prosemirror_json(sample_html_6)
    print("\nSample 6 HTML:", sample_html_6)
    print("JSON Output 6:", json_output_6)

    sample_html_7 = "<p> leading and trailing spaces </p>"
    json_output_7 = convert_html_to_prosemirror_json(sample_html_7)
    print("\nSample 7 HTML:", sample_html_7)
    print("JSON Output 7:", json_output_7)

    sample_html_8 = "   Leading text outside tags. <p>Then a paragraph.</p>   "
    json_output_8 = convert_html_to_prosemirror_json(sample_html_8)
    print("\nSample 8 HTML:", sample_html_8)
    print("JSON Output 8:", json_output_8)

    sample_html_9 = "<p>Text with <strong>bold <em>and italic</em></strong>.</p>"
    json_output_9 = convert_html_to_prosemirror_json(sample_html_9)
    print("\nSample 9 HTML:", sample_html_9)
    print("JSON Output 9:", json_output_9)

    # --- Testing Table Conversion --- (Keep existing table tests)
    # ... (Assume existing table tests are here from previous __main__ block) ...
    # Add new task list example:
    print("\n--- Testing Task List Conversion ---")
    sample_html_task_list = """
    <ul class="task-list">
      <li class="task-list-item" data-task-id="1" data-task-status="complete"><span class="task-item-body">Completed task</span></li>
      <li class="task-list-item" data-task-id="2" data-task-status="incomplete"><span class="task-item-body">Open task with <strong>style</strong></span></li>
      <li class="task-list-item" data-task-id="3" data-task-status="incomplete">Task with input <input type="checkbox" disabled /></li>
    </ul>
    """
    json_output_tasks = convert_html_to_prosemirror_json(sample_html_task_list)
    print("\nSample Task List HTML:", sample_html_task_list)
    print("JSON Output Task List:", json.dumps(json_output_tasks, indent=2))

    sample_html_image = '<p>Image: <img src="image.png"></p>' # Keep image test if it was here
    json_output_image = convert_html_to_prosemirror_json(sample_html_image)
    print("\nSample Image HTML:", sample_html_image) # Keep or merge with other image tests
    print("JSON Output Image:", json.dumps(json_output_image, indent=2))
