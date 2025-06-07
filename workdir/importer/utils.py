
import zipfile
import os
import shutil # For creating and removing temp directories

def extract_html_and_metadata_from_zip(zip_file_path, temp_extract_dir="temp_confluence_export"):
    """
    Extracts all HTML files and looks for common Confluence metadata files from a given ZIP archive.

    Args:
        zip_file_path (str): The path to the Confluence export ZIP file.
        temp_extract_dir (str): The directory where files will be temporarily extracted.

    Returns:
        tuple: (list_of_html_file_paths, metadata_file_path_or_None)
               Paths are absolute paths to the extracted files in the temp directory.
               Returns ([], None) if errors occur or no relevant files are found.
    """
    html_files = []
    metadata_file = None

    # Ensure temp_extract_dir is an absolute path or resolved correctly
    # For simplicity, assume it's relative to CWD or an absolute path is given.
    # If zip_file_path is relative, make it absolute from CWD of this script.
    # However, this script (utils.py) will run where it's called from, usually project root.

    # Let's assume zip_file_path is correctly pointing to the zip.
    # And temp_extract_dir will be created relative to the CWD when utils.py is run.

    if not os.path.exists(zip_file_path):
        print(f"Error: ZIP file not found at {zip_file_path}")
        return [], None

    # Clean up and create a temporary directory for extraction
    abs_temp_extract_dir = os.path.abspath(temp_extract_dir)
    if os.path.exists(abs_temp_extract_dir):
        shutil.rmtree(abs_temp_extract_dir)
    os.makedirs(abs_temp_extract_dir, exist_ok=True)

    print(f"Extracting ZIP file: {zip_file_path} to {abs_temp_extract_dir}")

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(abs_temp_extract_dir)

            for root, _, files in os.walk(abs_temp_extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file.lower().endswith(('.html', '.htm')):
                        html_files.append(os.path.abspath(file_path))
                    elif file.lower() in ('entities.xml', 'metadata.json', 'exportinfo.xml', 'space.json'):
                        if metadata_file:
                            print(f"Warning: Multiple potential metadata files found. Using first one: {metadata_file}")
                        else:
                            metadata_file = os.path.abspath(file_path)
                            print(f"Found potential metadata file: {metadata_file}")

        if not html_files:
            print(f"No HTML files found in the archive.") # Removed path for brevity
        if not metadata_file:
            print(f"No common metadata file found in the archive.")

        return html_files, metadata_file

    except zipfile.BadZipFile:
        print(f"Error: Invalid or corrupted ZIP file: {zip_file_path}")
        if os.path.exists(abs_temp_extract_dir):
            shutil.rmtree(abs_temp_extract_dir)
        return [], None
    except Exception as e:
        print(f"An error occurred during ZIP extraction: {e}")
        if os.path.exists(abs_temp_extract_dir):
            shutil.rmtree(abs_temp_extract_dir)
        return [], None

def cleanup_temp_extraction_dir(temp_extract_dir="temp_confluence_export"):
    """Removes the temporary extraction directory."""
    abs_temp_extract_dir = os.path.abspath(temp_extract_dir)
    if os.path.exists(abs_temp_extract_dir):
        try:
            shutil.rmtree(abs_temp_extract_dir)
            print(f"Successfully cleaned up temporary directory: {abs_temp_extract_dir}")
        except Exception as e:
            print(f"Error cleaning up temporary directory {abs_temp_extract_dir}: {e}")
    else:
        print(f"Temporary directory {abs_temp_extract_dir} not found, no cleanup needed.")

if __name__ == '__main__':
    # This block runs when script is executed directly: python importer/utils.py
    # It will run relative to the CWD where the command is issued.
    # If run from /app/workdir, paths will be relative to /app/workdir.

    print("Running example usage of ZIP extraction utility (from importer.utils)...")

    # Define paths relative to script execution CWD (e.g. /app/workdir if run from there)
    example_base_dir = "importer_utils_example_temp" # Temp dir for creating example content
    dummy_zip_path = os.path.join(example_base_dir, "test_export.zip")
    temp_dir_for_test = os.path.join(example_base_dir, "test_extraction_temp")
    dummy_content_root = os.path.join(example_base_dir, "dummy_content")

    # Ensure clean state for example
    if os.path.exists(example_base_dir):
        shutil.rmtree(example_base_dir)
    os.makedirs(os.path.join(dummy_content_root, "html_pages"), exist_ok=True)
    os.makedirs(os.path.join(dummy_content_root, "attachments"), exist_ok=True)

    with open(os.path.join(dummy_content_root, "html_pages/page1.html"), "w") as f: f.write("<h1>Page 1</h1>")
    with open(os.path.join(dummy_content_root, "html_pages/page2.htm"), "w") as f: f.write("<h1>Page 2</h1>")
    with open(os.path.join(dummy_content_root, "entities.xml"), "w") as f: f.write("<xml>metadata</xml>")
    with open(os.path.join(dummy_content_root, "attachments/image.png"), "wb") as f: f.write(b"dummyimagedata")

    with zipfile.ZipFile(dummy_zip_path, 'w') as zf:
        zf.write(os.path.join(dummy_content_root, "html_pages/page1.html"), arcname="html_pages/page1.html")
        zf.write(os.path.join(dummy_content_root, "html_pages/page2.htm"), arcname="html_pages/page2.htm")
        zf.write(os.path.join(dummy_content_root, "entities.xml"), arcname="entities.xml")
        zf.write(os.path.join(dummy_content_root, "attachments/image.png"), arcname="attachments/image.png")
    print(f"Created dummy ZIP: {os.path.abspath(dummy_zip_path)}")

    html_results, meta_result = extract_html_and_metadata_from_zip(dummy_zip_path, temp_extract_dir=temp_dir_for_test)

    if html_results:
        print("\nFound HTML files:")
        for p in html_results:
            print(p) # These will be absolute paths within temp_dir_for_test
    if meta_result:
        print(f"\nFound metadata file: {meta_result}") # Absolute path

    # Cleanup for the __main__ example run
    # The cleanup_temp_extraction_dir is for the main function, not this example's temp dir
    if os.path.exists(temp_dir_for_test): # Explicitly clean up example's extraction dir
         shutil.rmtree(temp_dir_for_test)
         print(f"Cleaned up example extraction temp: {os.path.abspath(temp_dir_for_test)}")

    if os.path.exists(example_base_dir): # Clean up the base directory for example files
        shutil.rmtree(example_base_dir)
        print(f"Cleaned up example base directory: {os.path.abspath(example_base_dir)}")
    print("Example usage finished.")
