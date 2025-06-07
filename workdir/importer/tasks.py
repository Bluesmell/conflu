
from celery import shared_task
import time
import random # For simulation (if any legacy parts use it, not in current task)
import os
import zipfile
import shutil # For cleanup_temp_extraction_dir and __main__ in utils/parser

from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic
# from django.apps import apps # Not currently used, but might be for model access

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def import_confluence_space(self, uploaded_file_id, user_id, dummy_zip_path_for_testing=None):
    # Args:
    #   uploaded_file_id: ID of a (future) model instance storing uploaded ZIP file info.
    #   user_id: ID of the user who initiated the import.
    #   dummy_zip_path_for_testing: Actual path to a ZIP file for this PoC.

    print(f"[Importer Task] ID {self.request.id} | Starting import_confluence_space for uploaded_file_id: {uploaded_file_id}, by user_id: {user_id}")

    zip_file_actual_path = None
    if dummy_zip_path_for_testing:
        # Ensure the dummy_zip_path_for_testing is absolute or resolvable from CWD
        # Celery worker CWD is typically the project root (/app/workdir)
        if not os.path.isabs(dummy_zip_path_for_testing):
            # Assuming worker CWD is /app/workdir, and path is relative to it
            # For this subtask, the dummy zip is created in /app/workdir/
            zip_file_actual_path = os.path.join(os.getcwd(), dummy_zip_path_for_testing)
        else:
            zip_file_actual_path = dummy_zip_path_for_testing
        print(f"[Importer Task] ID {self.request.id} | Using dummy_zip_path_for_testing: {zip_file_actual_path}")
    else:
        print(f"[Importer Task] ID {self.request.id} | ERROR: dummy_zip_path_for_testing not provided for this PoC.")
        # In real scenario:
        # UploadedFileModel = apps.get_model('importer', 'ConfluenceUpload')
        # try:
        #     upload_record = UploadedFileModel.objects.get(pk=uploaded_file_id)
        #     zip_file_actual_path = upload_record.file.path
        #     # upload_record.status = 'PROCESSING'; upload_record.save()
        # except UploadedFileModel.DoesNotExist:
        #     print(f"[Importer Task] ID {self.request.id} | ERROR: UploadedFile record {uploaded_file_id} not found.")
        #     return f"UploadedFile record {uploaded_file_id} not found."
        return f"dummy_zip_path_for_testing not provided for PoC for {uploaded_file_id}."

    # Ensure the provided dummy zip actually exists before proceeding
    if not os.path.exists(zip_file_actual_path):
        print(f"[Importer Task] ID {self.request.id} | ERROR: Dummy ZIP file for testing not found at {zip_file_actual_path}.")
        return f"Dummy ZIP for testing not found at {zip_file_actual_path} for {uploaded_file_id}."

    # Unique temp directory for this task instance
    temp_extraction_main_dir = f"temp_confluence_export_{self.request.id or uploaded_file_id}"
    abs_temp_extraction_main_dir = os.path.join(os.getcwd(), temp_extraction_main_dir)


    final_message = f"Import task for {uploaded_file_id} encountered an issue."
    try:
        print(f"[Importer Task] ID {self.request.id} | Extracting to: {abs_temp_extraction_main_dir}")
        html_files, metadata_file = extract_html_and_metadata_from_zip(
            zip_file_actual_path,
            temp_extract_dir=abs_temp_extraction_main_dir # Pass absolute path
        )

        if not html_files:
            print(f"[Importer Task] ID {self.request.id} | No HTML files extracted from {zip_file_actual_path}.")
            final_message = f"No HTML files found in ZIP for {uploaded_file_id}."
            # upload_record.status = 'FAILED'; upload_record.error_message = final_message; upload_record.save()
            return final_message # Return early

        if metadata_file:
            print(f"[Importer Task] ID {self.request.id} | Metadata file found: {metadata_file}. Further processing would occur here.")

        parsed_data_summary = []
        for i, html_path in enumerate(html_files[:2]): # Process up to 2 files for PoC
            print(f"[Importer Task] ID {self.request.id} | Parsing HTML file ({i+1}/{len(html_files[:2])}): {html_path}")
            basic_info = parse_html_file_basic(html_path) # html_path is already absolute
            if basic_info:
                parsed_data_summary.append({
                    "file": os.path.basename(html_path),
                    "title": basic_info.get("title"),
                    "h1_count": len(basic_info.get("h1_tags", []))
                })
            else:
                print(f"[Importer Task] ID {self.request.id} | Failed to parse {html_path} or no info extracted.")

        if parsed_data_summary:
            print(f"[Importer Task] ID {self.request.id} | Summary of parsed data (first 2 files):")
            for item in parsed_data_summary:
                print(f"  - File: {item['file']}, Title: {item['title']}, H1s: {item['h1_count']}")

        print(f"[Importer Task] ID {self.request.id} | Basic parsing PoC complete for {uploaded_file_id}.")
        final_message = f"Import task for {uploaded_file_id} finished basic parsing PoC. Parsed {len(parsed_data_summary)} HTML files."
        # upload_record.status = 'COMPLETED'; upload_record.save()

    except Exception as e:
        print(f"[Importer Task] ID {self.request.id} | CRITICAL ERROR during import for {uploaded_file_id}: {e}")
        # upload_record.status = 'FAILED'; upload_record.error_message = str(e); upload_record.save()
        # self.retry(exc=e) # Optionally retry
        final_message = f"Import task for {uploaded_file_id} FAILED: {e}"
    finally:
        cleanup_temp_extraction_dir(temp_extract_dir=abs_temp_extraction_main_dir) # Use absolute path
        # Clean up the dummy zip if it was specifically created for this task test run and path indicates it
        if dummy_zip_path_for_testing and "created_for_task_test" in dummy_zip_path_for_testing: # Example flag in path
            if os.path.exists(zip_file_actual_path): # Use resolved absolute path
                os.remove(zip_file_actual_path)
                print(f"[Importer Task] ID {self.request.id} | Cleaned up dummy test ZIP: {zip_file_actual_path}")
            # Also remove the source directory if it follows a pattern
            dummy_source_dir = os.path.join(os.getcwd(), "dummy_content_task_test_" + str(uploaded_file_id)) # Example pattern
            if "dummy_content_task_test" in dummy_zip_path_for_testing and os.path.exists(dummy_source_dir):
                 shutil.rmtree(dummy_source_dir)
                 print(f"[Importer Task] ID {self.request.id} | Cleaned up dummy source dir: {dummy_source_dir}")
    return final_message
