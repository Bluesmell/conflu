from bs4 import BeautifulSoup
import os
# import re # For more complex attribute filtering if needed, or simple string ops (Not used in current version)
from urllib.parse import unquote # For decoding URL-encoded attachment names

def parse_html_file_basic(html_file_path): # Renamed from parse_html_file_advanced to replace existing
    """
    Parses a Confluence HTML file using BeautifulSoup, extracts title,
    main content HTML, and referenced attachments.
    (This is the enhanced version)
    """
    extracted_data = {
        "title": None,
        "main_content_html": None,
        "referenced_attachments": [] # List of attachment filenames/paths
    }

    print(f"Enhanced parsing HTML file: {html_file_path}")
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')

        # 1. Extract Title
        if soup.title and soup.title.string:
            extracted_data["title"] = soup.title.string.strip()
            print(f"  Title: {extracted_data['title']}")
        else: # Fallback to first H1 if no title tag
            h1_tag = soup.find('h1')
            if h1_tag:
                extracted_data["title"] = h1_tag.get_text(separator=' ', strip=True)
                print(f"  Title (from H1): {extracted_data['title']}")


        # 2. Extract Main Content HTML
        main_content_area = None
        selectors = [
            'div.wiki-content',
            '#main-content',
            '#content',
            'body'
        ]

        for selector in selectors:
            if selector.startswith('#'): # ID selector
                main_content_area = soup.find(id=selector.lstrip('#'))
            elif selector.startswith('.'): # Class selector
                # Ensure it's a div with that class, or search for any tag if not specified (original assumed div)
                main_content_area = soup.find('div', class_=selector.lstrip('.'))
            else: # Tag name selector
                main_content_area = soup.find(selector)

            if main_content_area:
                print(f"  Found content area with selector: '{selector}'")
                break

        if main_content_area:
            extracted_data["main_content_html"] = main_content_area.decode_contents()
        else:
            print(f"  Could not find a specific main content div, using whole body or None.")
            body_tag = soup.find('body')
            if body_tag:
                extracted_data["main_content_html"] = body_tag.decode_contents()
            else:
                extracted_data["main_content_html"] = html_content


        # 3. Extract Referenced Attachments
        search_area_for_attachments = main_content_area if main_content_area else soup

        if search_area_for_attachments:
            attachments_found = set()

            for img_tag in search_area_for_attachments.find_all('img', src=True):
                src = img_tag['src']
                if "attachments/" in src or not (src.startswith("http:") or src.startswith("https:") or src.startswith("//")):
                    filename = os.path.basename(unquote(src.split('?')[0]))
                    if filename:
                       attachments_found.add(filename)

            for a_tag in search_area_for_attachments.find_all('a', href=True):
                href = a_tag['href']
                if ("attachments/" in href or not (href.startswith("http:") or href.startswith("https:") or href.startswith("//") or href.startswith("#"))):
                    filename = os.path.basename(unquote(href.split('?')[0]))
                    if filename:
                        attachments_found.add(filename)

            extracted_data["referenced_attachments"] = sorted(list(attachments_found))
            if extracted_data["referenced_attachments"]:
                print(f"  Found referenced attachments: {extracted_data['referenced_attachments']}")
            else:
                print(f"  No specific referenced attachments found in links or images.")

        # Check for effectively empty or invalid content post-parsing
        title_present = extracted_data.get("title") and extracted_data.get("title").strip()
        content_html = extracted_data.get("main_content_html", "")
        # If no title AND (content is empty OR content is very short e.g. < 5 chars and might be garbage)
        # This specifically helps the test case with b"\0\1\2" which results in title=None, content='\x00\x01\x02'
        if not title_present and (not content_html.strip() or len(content_html.strip()) < 5) :
            if "error" not in extracted_data: # Don't overwrite an error from an actual exception
                extracted_data["error"] = "Failed to extract meaningful title or content."

        return extracted_data

    except FileNotFoundError:
        print(f"Error: HTML file not found at {html_file_path}")
        return None
    except Exception as e:
        print(f"An error occurred during enhanced HTML parsing of {html_file_path}: {e}")
        return {
            "title": extracted_data.get("title"), # Return partial data if possible
            "main_content_html": extracted_data.get("main_content_html"),
            "referenced_attachments": [],
            "error": str(e)
        }

if __name__ == '__main__':
    import shutil

    print("Running example usage of Enhanced HTML parser (from importer.parser)...")
    example_base_dir = "importer_parser_example_temp_enhanced" # Changed dir name for clarity
    dummy_html_path = os.path.join(example_base_dir, "test_enhanced_page.html")

    if os.path.exists(example_base_dir):
        shutil.rmtree(example_base_dir)
    os.makedirs(example_base_dir, exist_ok=True)

    dummy_html_content = """
    <html>
    <head><title> My Enhanced Test Page </title></head>
    <body>
        <div id="header"><h1>Page Title in Header (should not be main)</h1></div>
        <div class="wiki-content">
            <h1>Main Content Heading</h1>
            <p>This is the <em>main content</em> of the page.</p>
            <p>It includes an image: <img src="../attachments/image.png" alt="Test Image"></p>
            <p>And a link to a document: <a href="attachments/document.pdf">View Document</a></p>
            <p>Another link: <a href="http://example.com/external.html">External Link</a></p>
            <p>Page anchor: <a href="#section1">Section 1</a></p>
            <p>Image with query params: <img src="attachments/photo.jpg?version=2" alt="Photo"></p>
            <p>Encoded name: <a href="attachments/My%20CV.docx">My CV</a></p>
        </div>
        <div id="footer"><p>Copyright 2023</p></div>
    </body>
    </html>
    """
    with open(dummy_html_path, "w", encoding="utf-8") as f:
        f.write(dummy_html_content)
    print(f"Created dummy HTML file: {os.path.abspath(dummy_html_path)}")

    # Call the updated parse_html_file_basic
    parsed_info = parse_html_file_basic(dummy_html_path)

    if parsed_info:
        print("\nParsed Information (Enhanced):")
        print(f"  Title: {parsed_info.get('title')}")
        print(f"  Main Content HTML (first 100 chars): {parsed_info.get('main_content_html', '')[:100]}...")
        print(f"  Referenced Attachments: {parsed_info.get('referenced_attachments')}")
        if parsed_info.get('error'):
            print(f"  Error during parsing: {parsed_info.get('error')}")

    if os.path.exists(example_base_dir):
        shutil.rmtree(example_base_dir)
        print(f"Cleaned up example base directory: {os.path.abspath(example_base_dir)}")
    print("Enhanced HTML parser example usage finished.")

import xml.etree.ElementTree as ET

def parse_confluence_metadata_for_hierarchy(metadata_file_path):
    """
    Parses a Confluence metadata XML file (e.g., entities.xml) to extract page hierarchy.

    Args:
        metadata_file_path (str): Path to the metadata XML file.

    Returns:
        list: A list of dictionaries, where each dictionary represents a page
              and contains 'id', 'title', and 'parent_id' (which can be None).
              Returns an empty list if parsing fails or file not found.
    """
    hierarchy_data = []

    if not metadata_file_path or not os.path.exists(metadata_file_path):
        print(f"Metadata file not found or path is invalid: {metadata_file_path}")
        return hierarchy_data

    try:
        tree = ET.parse(metadata_file_path)
        root = tree.getroot()

        for obj_element in root.findall(".//object[@class='Page']"):
            page_info = {'id': None, 'title': None, 'parent_id': None}

            id_prop = obj_element.find("./property[@name='id']/long")
            if id_prop is not None and id_prop.text:
                page_info['id'] = id_prop.text.strip()

            title_prop = obj_element.find("./property[@name='title']/string")
            if title_prop is not None and title_prop.text:
                page_info['title'] = title_prop.text.strip()
            elif title_prop is None:
                 title_prop_alt = obj_element.find("./property[@name='title']")
                 if title_prop_alt is not None and title_prop_alt.text and not title_prop_alt.findall("*"):
                     page_info['title'] = title_prop_alt.text.strip()

            parent_prop = obj_element.find("./property[@name='parent']")
            if parent_prop is not None:
                parent_id_elem = parent_prop.find("./id")
                if parent_id_elem is not None and parent_id_elem.text:
                    page_info['parent_id'] = parent_id_elem.text.strip()
                else:
                    parent_obj_id_prop = parent_prop.find("./object[@class='Page']/property[@name='id']/long")
                    if parent_obj_id_prop is not None and parent_obj_id_prop.text:
                         page_info['parent_id'] = parent_obj_id_prop.text.strip()

            if page_info['parent_id'] is None:
                parent_page_prop = obj_element.find("./property[@name='parentPage']/id")
                if parent_page_prop is not None and parent_page_prop.text:
                    page_info['parent_id'] = parent_page_prop.text.strip()

            if page_info['id']:
                hierarchy_data.append(page_info)
            else:
                print(f"  Skipping an <object class='Page'> element, could not determine its ID.")

    except ET.ParseError as e:
        print(f"Error parsing XML metadata file {metadata_file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while parsing metadata {metadata_file_path}: {e}")

    if not hierarchy_data:
        print(f"No hierarchy data extracted from {metadata_file_path}. Check XML structure and parsing logic.")

    return hierarchy_data

# This __main__ block is for the new metadata parser.
# The existing __main__ block above is for parse_html_file_basic.
# For clarity in a real file, these might be merged or put in separate test scripts.
if __name__ == '__main__':
    # This condition will now also be true when running `python workdir/importer/parser.py`
    # So, both __main__ blocks will execute. This is fine for now.
    # A better structure might be to use a command-line argument parser if direct script execution is common.

    # Temporarily ensure 'shutil' is available for this block too, if it was only imported in the first __main__
    import shutil # If not already globally available in the script. os is global from HTML parser.

    print("\nTesting Confluence Metadata Parser...")
    sample_xml_content = """
    <hibernate-generic>
        <object class="Page">
            <property name="id"><long>101</long></property>
            <property name="title"><string>Parent Page</string></property>
        </object>
        <object class="Page">
            <property name="id"><long>102</long></property>
            <property name="title"><string>Child Page 1</string></property>
            <property name="parent"><id>101</id></property>
        </object>
        <object class="Page">
            <property name="id"><long>103</long></property>
            <property name="title"><string>Child Page 2</string></property>
            <property name="parent">
                <object class="Page">
                    <property name="id"><long>101</long></property>
                </object>
            </property>
        </object>
        <object class="Space">
            <property name="id"><long>201</long></property>
            <property name="name"><string>My Space</string></property>
        </object>
        <object class="Page">
             <property name="title"><string>Orphan Page No ID</string></property>
        </object>
    </hibernate-generic>
    """
    temp_xml_file = "temp_entities_test.xml" # Created in current working directory
    with open(temp_xml_file, "w", encoding="utf-8") as f:
        f.write(sample_xml_content)

    hierarchy = parse_confluence_metadata_for_hierarchy(temp_xml_file)
    print("Extracted Hierarchy:")
    for item in hierarchy:
        print(item)

    if os.path.exists(temp_xml_file):
        os.remove(temp_xml_file)
    print("Metadata parser test finished.")
