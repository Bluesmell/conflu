
from celery import shared_task
import os
import re # For extracting page ID from filename
import shutil
import zipfile # Keep for context

from celery import shared_task

from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic # This now returns title, main_content_html, referenced_attachments
from .models import ConfluenceUpload
from .converter import convert_html_to_prosemirror_json # New import

# Imports for Page model and Workspace
from django.contrib.auth import get_user_model
from pages.models import Page, Attachment # Added Attachment
from django.core.files import File # New import for Django File wrapper
import mimetypes # New import for guessing MIME types

try:
    from workspaces.models import Workspace # Assuming workspaces app is in INSTALLED_APPS
except ImportError:
    print("WARNING: Workspace model could not be imported in tasks.py. Page creation will likely fail or use a placeholder.")
    Workspace = None # Placeholder to allow file to load if Workspace app is problematic during startup

User = get_user_model()


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def import_confluence_space(self, confluence_upload_id):
    try:
        upload_record = ConfluenceUpload.objects.get(pk=confluence_upload_id)
    except ConfluenceUpload.DoesNotExist:
        print(f"[Importer Task] CRITICAL: ConfluenceUpload record {confluence_upload_id} not found. Aborting.")
        return f"ConfluenceUpload record {confluence_upload_id} not found."

    upload_record.status = ConfluenceUpload.STATUS_PROCESSING
    upload_record.task_id = self.request.id # Store Celery task ID
    upload_record.save()

    importer_user = upload_record.user # User who initiated the import

    print(f"[Importer Task] ID {self.request.id} | Starting import for ConfluenceUpload ID: {confluence_upload_id} by User: {importer_user.username if importer_user else 'Unknown'}")
    zip_file_actual_path = upload_record.file.path

    if not os.path.exists(zip_file_actual_path):
        error_message = f"Uploaded ZIP file not found at path: {zip_file_actual_path} for Upload ID {confluence_upload_id}."
        print(f"[Importer Task] ID {self.request.id} | ERROR: {error_message}")
        upload_record.status = ConfluenceUpload.STATUS_FAILED
        # upload_record.error_message = error_message # If model had an error field
        upload_record.save()
        return error_message

    temp_extraction_main_dir = f"temp_confluence_export_{self.request.id}"
    abs_temp_extraction_main_dir = os.path.join(os.getcwd(), temp_extraction_main_dir)

    # Workspace logic: Attempt to get a default workspace.
    # This is a placeholder strategy. A real app might require user to specify workspace.
    default_workspace = None
    if Workspace: # Check if Workspace model was successfully imported
        default_workspace = Workspace.objects.first()
        if not default_workspace:
            print(f"[Importer Task] ID {self.request.id} | WARNING: No default workspace found. Pages might not be assigned a workspace if model requires it.")
    else:
        print(f"[Importer Task] ID {self.request.id} | WARNING: Workspace model not available. Cannot assign workspace to pages.")

    pages_created_count = 0
    pages_failed_count = 0
    final_task_message = f"Import task for Upload ID {confluence_upload_id} processing completed." # Default message

    try:
        html_files, metadata_file = extract_html_and_metadata_from_zip(
            zip_file_actual_path,
            temp_extract_dir=abs_temp_extraction_main_dir
        )

        if not html_files:
            message = f"No HTML files found in ZIP for Upload ID {confluence_upload_id}."
            print(f"[Importer Task] ID {self.request.id} | {message}")
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            final_task_message = message
            # upload_record.save() will be handled in finally
            return final_task_message # Return early

        if metadata_file:
            print(f"[Importer Task] ID {self.request.id} | Metadata file found: {metadata_file}. (Metadata processing not yet implemented)")
            # TODO: Process metadata_file for hierarchy, proper original IDs, etc.

        # --- Loop through all HTML files (removed [:2] slice) ---
        for i, html_path in enumerate(html_files):
            print(f"[Importer Task] ID {self.request.id} | Processing HTML file ({i+1}/{len(html_files)}): {html_path}")

            parsed_page_data = parse_html_file_basic(html_path) # Enhanced parser

            if not parsed_page_data or parsed_page_data.get("error"): # Check for parser error
                error_info = parsed_page_data.get('error', 'no main content or parser error') if parsed_page_data else 'parser returned None'
                print(f"[Importer Task] ID {self.request.id} | Skipping file {html_path} due to: {error_info}.")
                pages_failed_count += 1
                continue

            if not parsed_page_data.get("main_content_html"):
                print(f"[Importer Task] ID {self.request.id} | Skipping file {html_path} because no main_content_html was extracted.")
                pages_failed_count += 1
                continue

            page_title = parsed_page_data.get("title", os.path.splitext(os.path.basename(html_path))[0])
            main_content_html = parsed_page_data.get("main_content_html")
            # referenced_attachments = parsed_page_data.get("referenced_attachments", []) # Will be used in Part 2

            # Convert HTML to ProseMirror JSON
            content_json = convert_html_to_prosemirror_json(main_content_html)

            # Heuristic for original Confluence ID from filename
            original_confluence_page_id = None
            filename_base = os.path.basename(html_path)
            # Try to find numbers that might be IDs, e.g., "Page Name_12345.html" or "12345.html"
            match = re.search(r'_(\d+)\.html$', filename_base) or re.search(r'^(\d+)\.html$', filename_base)
            if match:
                original_confluence_page_id = match.group(1)
                print(f"  Extracted original_confluence_page_id: {original_confluence_page_id} from filename: {filename_base}")
            else:
                print(f"  Could not extract numeric original_confluence_page_id from filename: {filename_base}")

            try:
                # Page model requires a 'space'. The current Page model uses 'space', not 'workspace'.
                # This part needs to align with the actual Page model's foreign key to Space.
                # For now, this subtask focuses on getting up to Page creation.
                # The default_workspace might contain spaces, or a default space needs to be chosen.
                # This is a known simplification point from the prompt.
                # Assuming Page model requires 'workspace' and it can be None if model allows.
                # The actual Page model created uses 'space', related to 'Workspace'.
                # This needs careful handling: for now, we'll pass default_workspace if the Page model expects 'workspace'.
                # If Page model expects 'space_id', this will fail or need adjustment.
                # The Page model in pages.models has 'space = models.ForeignKey(Space, ...)'
                # So, we need a Space instance.

                target_space = None
                if default_workspace and hasattr(default_workspace, 'space_set') and default_workspace.space_set.exists():
                    target_space = default_workspace.space_set.first() # Use first space of the default workspace

                if not target_space:
                    print(f"[Importer Task] ID {self.request.id} | ERROR: No target Space available for page '{page_title}'. Skipping page creation.")
                    pages_failed_count +=1
                    continue

                # Duplicate check
                if original_confluence_page_id:
                    if Page.objects.filter(original_confluence_id=original_confluence_page_id, space=target_space).exists():
                        print(f"  Page with original_confluence_id '{original_confluence_page_id}' already exists in space '{target_space.name}'. Skipping.")
                        pages_failed_count += 1
                        continue

                created_page_object = Page.objects.create( # Store created page
                    title=page_title,
                    content_json=content_json,
                    space=target_space, # Assigning to the determined space
                    imported_by=importer_user,
                    original_confluence_id=original_confluence_page_id
                    # parent_page handling later
                )
                pages_created_count += 1
                print(f"  Successfully created Page: '{created_page_object.title}' in Space '{target_space.name}' (ID: {created_page_object.id})")

                # --- Part 2: Attachment Processing ---
                referenced_attachments = parsed_page_data.get("referenced_attachments", [])
                attachments_created_count_for_page = 0

                if referenced_attachments:
                    print(f"    Found {len(referenced_attachments)} referenced attachments for page '{created_page_object.title}'. Processing...")

                    for attachment_ref_name in referenced_attachments:
                        potential_paths_to_try = [
                            os.path.join(os.path.dirname(html_path), attachment_ref_name),
                            os.path.join(os.path.dirname(html_path), "attachments", attachment_ref_name),
                            os.path.join(abs_temp_extraction_main_dir, "attachments", attachment_ref_name),
                            os.path.join(abs_temp_extraction_main_dir, attachment_ref_name),
                        ]

                        attachment_file_path_found = None
                        for p_path in potential_paths_to_try:
                            if os.path.exists(p_path) and os.path.isfile(p_path):
                                attachment_file_path_found = p_path
                                print(f"      Located attachment '{attachment_ref_name}' at: {attachment_file_path_found}")
                                break

                        if attachment_file_path_found:
                            try:
                                mime_type_guess, _ = mimetypes.guess_type(attachment_file_path_found)

                                with open(attachment_file_path_found, 'rb') as f:
                                    django_file = File(f, name=os.path.basename(attachment_ref_name))

                                    Attachment.objects.create(
                                        page=created_page_object,
                                        original_filename=os.path.basename(attachment_ref_name),
                                        file=django_file,
                                        mime_type=mime_type_guess if mime_type_guess else 'application/octet-stream',
                                        imported_by=importer_user
                                    )
                                attachments_created_count_for_page += 1
                                print(f"      Successfully created Attachment record for: {attachment_ref_name}")
                            except Exception as attach_create_error:
                                print(f"[Importer Task] ID {self.request.id} | ERROR creating attachment '{attachment_ref_name}' for page '{created_page_object.title}': {attach_create_error}")
                        else:
                            print(f"      WARNING: Could not locate attachment file '{attachment_ref_name}' for page '{created_page_object.title}' in checked paths.")

                if attachments_created_count_for_page > 0:
                     print(f"    Successfully processed {attachments_created_count_for_page} attachments for page '{created_page_object.title}'.")

            except Exception as page_create_error: # This except handles errors from Page.objects.create or attachment processing for that page
                pages_failed_count += 1
                print(f"[Importer Task] ID {self.request.id} | ERROR processing page '{page_title}' or its attachments: {page_create_error}")

        # Determine final status based on outcomes
        if pages_created_count > 0:
            upload_record.status = ConfluenceUpload.STATUS_COMPLETED
        elif len(html_files) > 0 and pages_failed_count == len(html_files): # All files processed resulted in failure/skip
             upload_record.status = ConfluenceUpload.STATUS_FAILED
        elif not html_files: # No files were found initially (status already set)
            pass # Keep the status set by the 'if not html_files:' block
        else: # Mix of success/failure or other conditions not leading to completion
             upload_record.status = ConfluenceUpload.STATUS_FAILED # Default to FAILED if no pages created or mixed results are unclear

        final_task_message = (f"Import task for Upload ID {confluence_upload_id} finished. "
                              f"Pages created: {pages_created_count}. Pages failed/skipped: {pages_failed_count}.")
        print(f"[Importer Task] ID {self.request.id} | {final_task_message}")

    except Exception as e:
        error_message_critical = f"CRITICAL ERROR during import for Upload ID {confluence_upload_id}: {e}"
        print(f"[Importer Task] ID {self.request.id} | {error_message_critical}")
        if 'upload_record' in locals() and upload_record: # Check if upload_record was fetched
            upload_record.status = ConfluenceUpload.STATUS_FAILED
        final_task_message = error_message_critical
        # self.retry(exc=e) # Consider if retry is appropriate
    finally:
        if 'upload_record' in locals() and upload_record: # Ensure upload_record is defined before saving
             upload_record.save()
        cleanup_temp_extraction_dir(temp_extract_dir=abs_temp_extraction_main_dir)
        final_status_to_log = upload_record.status if 'upload_record' in locals() and upload_record else 'Unknown (upload_record not found)'
        print(f"[Importer Task] ID {self.request.id} | Finished processing for ConfluenceUpload ID: {confluence_upload_id}. Final status: {final_status_to_log}")

    return final_task_message
