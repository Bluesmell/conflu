
from celery import shared_task
# import time # Removed as it's not used in the new logic
# import random # Removed as it's not used
import os
import zipfile # Ensure zipfile is imported
import shutil # For cleanup_temp_extraction_dir

from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic
from .models import ConfluenceUpload # New import

@shared_task(bind=True, max_retries=3, default_retry_delay=300) # Keep existing Celery decorators
def import_confluence_space(self, confluence_upload_id):
    try:
        upload_record = ConfluenceUpload.objects.get(pk=confluence_upload_id)
    except ConfluenceUpload.DoesNotExist:
        print(f"[Importer Task] CRITICAL: ConfluenceUpload record {confluence_upload_id} not found. Aborting.")
        return f"ConfluenceUpload record {confluence_upload_id} not found."

    # Update status to PROCESSING and store task ID
    upload_record.status = ConfluenceUpload.STATUS_PROCESSING
    upload_record.task_id = self.request.id
    upload_record.save()

    print(f"[Importer Task] ID {self.request.id} | Starting import for ConfluenceUpload ID: {confluence_upload_id} by User ID: {upload_record.user.id if upload_record.user else 'Unknown'}")

    zip_file_actual_path = upload_record.file.path

    if not os.path.exists(zip_file_actual_path):
        error_message = f"Uploaded ZIP file not found at path: {zip_file_actual_path} for Upload ID {confluence_upload_id}."
        print(f"[Importer Task] ID {self.request.id} | ERROR: {error_message}")
        upload_record.status = ConfluenceUpload.STATUS_FAILED
        # upload_record.error_message = error_message # If model had this field
        upload_record.save()
        return error_message

    # Unique temp directory for this task instance using its own ID
    temp_extraction_main_dir = f"temp_confluence_export_{self.request.id}"
    # Ensure CWD is as expected (project root /app/workdir for Celery worker)
    abs_temp_extraction_main_dir = os.path.join(os.getcwd(), temp_extraction_main_dir)

    final_task_message = f"Import task for Upload ID {confluence_upload_id} processing completed."
    try:
        print(f"[Importer Task] ID {self.request.id} | Extracting ZIP: {zip_file_actual_path} to: {abs_temp_extraction_main_dir}")

        html_files, metadata_file = extract_html_and_metadata_from_zip(
            zip_file_actual_path,
            temp_extract_dir=abs_temp_extraction_main_dir
        )

        if not html_files:
            message = f"No HTML files found in ZIP for Upload ID {confluence_upload_id}."
            print(f"[Importer Task] ID {self.request.id} | {message}")
            upload_record.status = ConfluenceUpload.STATUS_FAILED # Or COMPLETED if no HTML is not an error
            # upload_record.error_message = message
            upload_record.save()
            final_task_message = message
            return final_task_message # Return early

        if metadata_file:
            print(f"[Importer Task] ID {self.request.id} | Metadata file found: {metadata_file}. Processing would occur here.")
            # TODO: Process metadata_file

        parsed_data_summary = []
        # TODO: Remove limit ([:2]) for production. For now, keep it for PoC.
        for i, html_path in enumerate(html_files[:2]):
            print(f"[Importer Task] ID {self.request.id} | Parsing HTML file ({i+1}/{len(html_files[:2])}): {html_path}")
            basic_info = parse_html_file_basic(html_path)
            if basic_info:
                parsed_data_summary.append({
                    "file": os.path.basename(html_path),
                    "title": basic_info.get("title"),
                    "h1_count": len(basic_info.get("h1_tags", []))
                })
                # TODO: Save this parsed data to Page models.
            else:
                print(f"[Importer Task] ID {self.request.id} | Failed to parse {html_path} or no info extracted.")

        if parsed_data_summary:
            print(f"[Importer Task] ID {self.request.id} | Summary of parsed data (first {len(parsed_data_summary)} files):")
            for item in parsed_data_summary:
                print(f"  - File: {item['file']}, Title: {item['title']}, H1s: {item['h1_count']}")

        # TODO: Implement actual data saving to database models (Page, Attachment etc.)

        upload_record.status = ConfluenceUpload.STATUS_COMPLETED
        upload_record.save()
        final_task_message = f"Import task for Upload ID {confluence_upload_id} finished basic parsing. Parsed {len(parsed_data_summary)} HTML files."
        print(f"[Importer Task] ID {self.request.id} | {final_task_message}")

    except Exception as e:
        # Catch any exception during processing
        error_message_critical = f"CRITICAL ERROR during import for Upload ID {confluence_upload_id}: {e}"
        print(f"[Importer Task] ID {self.request.id} | {error_message_critical}")

        upload_record.status = ConfluenceUpload.STATUS_FAILED
        # upload_record.error_message = str(e) # Store the error
        upload_record.save()

        final_task_message = error_message_critical
        # self.retry(exc=e) # Optionally retry for certain types of errors
    finally:
        # Ensure cleanup happens
        cleanup_temp_extraction_dir(temp_extract_dir=abs_temp_extraction_main_dir)
        print(f"[Importer Task] ID {self.request.id} | Finished processing for ConfluenceUpload ID: {confluence_upload_id}. Final status: {upload_record.status}")

    return final_task_message
