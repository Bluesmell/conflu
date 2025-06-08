from bs4 import BeautifulSoup, NavigableString, Tag

def map_tag_to_prosemirror_type(tag_name):
    """Maps HTML tag names to ProseMirror node or mark types."""
    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        return 'heading'
    return {
        'p': 'paragraph',
        'ul': 'bullet_list',
        'ol': 'ordered_list',
        'li': 'list_item',
        'br': 'hard_break',
    }.get(tag_name, None)

def get_heading_attrs(tag_name):
    """Returns attributes for a heading node, like level."""
    if tag_name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
        return {'level': int(tag_name[1])}
    return {}

def process_node(node, current_marks=None):
    """
    Recursively processes a BeautifulSoup node and its children
    to generate ProseMirror JSON fragments.
    """
    if current_marks is None:
        current_marks = []

    content_fragments = []

    if isinstance(node, NavigableString):
        text_content = str(node) # Keep original whitespace for now, strip later if needed at block level
        if text_content:
            fragment = {"type": "text", "text": text_content}
            if current_marks:
                fragment["marks"] = current_marks[:]
            return [fragment]
        return []

    elif isinstance(node, Tag):
        node_type = map_tag_to_prosemirror_type(node.name)
        new_marks = current_marks[:]

        mark_type = None
        mark_attrs = {}

        if node.name in ['strong', 'b']:
            mark_type = 'bold'
        elif node.name in ['em', 'i']:
            mark_type = 'italic'
        elif node.name == 'a' and node.has_attr('href'):
            mark_type = 'link'
            mark_attrs = {"href": node['href']}

        if mark_type:
            # Add mark if not already active with same attrs (simplification for now)
            is_active = False
            for m in new_marks:
                if m['type'] == mark_type:
                    if mark_type != 'link' or (mark_type == 'link' and m.get('attrs') == mark_attrs):
                        is_active = True
                        break
            if not is_active:
                mark_to_add = {"type": mark_type}
                if mark_attrs:
                    mark_to_add["attrs"] = mark_attrs
                new_marks.append(mark_to_add)

        child_content = []
        for child in node.children:
            child_content.extend(process_node(child, new_marks))

        # Strip leading/trailing whitespace text nodes from block elements if they are sole children
        # This is a basic attempt to clean up common whitespace issues.
        if node_type and child_content:
            if len(child_content) == 1 and child_content[0]['type'] == 'text':
                child_content[0]['text'] = child_content[0]['text'].strip()
                if not child_content[0]['text']: # If stripping makes it empty
                    child_content = []


        if not child_content and node.name not in ['br', 'img']:
            return []

        if node_type:
            pm_node = {"type": node_type}
            if child_content:
                pm_node["content"] = child_content

            attrs = get_heading_attrs(node.name)
            if attrs:
                pm_node["attrs"] = attrs

            return [pm_node]

        elif mark_type:
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
