
from bs4 import BeautifulSoup
import os # Required for os.path in __main__ example

def parse_html_file_basic(html_file_path):
    """
    Parses an HTML file using BeautifulSoup and extracts basic information as a PoC.
    Currently, it extracts and prints the title and all H1 tags.

    Args:
        html_file_path (str): The absolute path to the HTML file.

    Returns:
        dict: A dictionary containing extracted basic info (e.g., title, h1s),
              or None if parsing fails.
    """
    extracted_data = {
        "title": None,
        "h1_tags": [],
        "paragraphs_sample": [] # Sample of first few paragraphs
    }

    print(f"Parsing HTML file (basic): {html_file_path}")
    try:
        with open(html_file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'lxml')

        if soup.title and soup.title.string:
            extracted_data["title"] = soup.title.string.strip()
            print(f"  Title: {extracted_data['title']}")

        for h1 in soup.find_all('h1'):
            if h1.string:
                extracted_data["h1_tags"].append(h1.string.strip())
            else:
                 extracted_data["h1_tags"].append(h1.get_text(separator=' ', strip=True))

        if extracted_data["h1_tags"]:
            print(f"  Found H1 tags: {extracted_data['h1_tags']}")
        else:
            print("  No H1 tags found.")

        for p_tag in soup.find_all('p', limit=3):
            extracted_data["paragraphs_sample"].append(p_tag.get_text(separator=' ', strip=True))

        if extracted_data["paragraphs_sample"]:
            print(f"  Paragraphs sample: {extracted_data['paragraphs_sample']}")
        else:
            print("  No paragraph tags found for sample.")

        return extracted_data

    except FileNotFoundError:
        print(f"Error: HTML file not found at {html_file_path}")
        return None
    except Exception as e:
        print(f"An error occurred during basic HTML parsing of {html_file_path}: {e}")
        return None

if __name__ == '__main__':
    # This block runs when script is executed directly: python importer/parser.py
    # It will run relative to the CWD where the command is issued.
    # If run from /app/workdir, paths will be relative to /app/workdir.
    import shutil # Ensure shutil is imported for __main__

    print("Running example usage of HTML parser utility (from importer.parser)...")

    # Define paths relative to script execution CWD (e.g. /app/workdir if run from there)
    example_base_dir = "importer_parser_example_temp"
    dummy_html_path = os.path.join(example_base_dir, "test_page.html")

    # Ensure clean state for example
    if os.path.exists(example_base_dir):
        shutil.rmtree(example_base_dir)
    os.makedirs(example_base_dir, exist_ok=True)

    dummy_html_content = """
    <html>
    <head><title> My Test Page Title </title></head>
    <body>
        <h1>First Main Heading</h1>
        <p>This is the first paragraph with some <strong>bold text</strong>.</p>
        <div class="content">
            <h1>Another H1 Inside a Div</h1>
            <p>Second paragraph here.</p>
            <p>Third paragraph with a <a href="#">link</a>.</p>
            <p>Fourth paragraph.</p>
        </div>
        <h1><span>Third H1 with a span</span></h1>
    </body>
    </html>
    """
    with open(dummy_html_path, "w", encoding="utf-8") as f:
        f.write(dummy_html_content)
    print(f"Created dummy HTML file: {os.path.abspath(dummy_html_path)}")

    parsed_info = parse_html_file_basic(dummy_html_path)

    if parsed_info:
        print("\nParsed Information:")
        print(f"  Title: {parsed_info.get('title')}")
        print(f"  H1s: {parsed_info.get('h1_tags')}")
        print(f"  Paras sample: {parsed_info.get('paragraphs_sample')}")

    if os.path.exists(example_base_dir): # Clean up the base directory for example files
        shutil.rmtree(example_base_dir)
        print(f"Cleaned up example base directory: {os.path.abspath(example_base_dir)}")
    print("Example usage finished.")
