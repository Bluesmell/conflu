from celery import shared_task
import os
import re
import shutil
import mimetypes

from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic, parse_confluence_metadata_for_hierarchy
from .models import ConfluenceUpload
from .converter import convert_html_to_prosemirror_json

from django.contrib.auth import get_user_model
from pages.models import Page, Attachment
from django.core.files import File

try:
    from workspaces.models import Workspace, Space
except ImportError:
    print("WARNING: Workspace/Space models could not be imported in tasks.py. Page creation might be affected.")
    Workspace = None
    Space = None

User = get_user_model()

def _resolve_symbolic_image_srcs(node_list, attachments_by_filename):
    if not isinstance(node_list, list): return
    for node in node_list:
        if not isinstance(node, dict): continue
        if node.get("type") == "image":
            attrs = node.get("attrs", {})
            src = attrs.get("src", "")
            if src.startswith("pm:attachment:"):
                filename = src.replace("pm:attachment:", "", 1)
                if filename in attachments_by_filename: attrs["src"] = attachments_by_filename[filename]
                else: print(f"    WARNING: Image attachment '{filename}' ref'd in content but not found. Symbolic src remains.")
        if "content" in node and isinstance(node["content"], list):
            _resolve_symbolic_image_srcs(node["content"], attachments_by_filename)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def import_confluence_space(self, confluence_upload_id):
    upload_record = None # Define upload_record in a broader scope for finally block
    error_list_for_details = []
    # Initialize local counters that will be synced to upload_record
    local_pages_succeeded_count = 0
    local_pages_failed_count = 0
    local_attachments_succeeded_count = 0
    pages_linked_count = 0 # Initialize pages_linked_count

    try:
        upload_record = ConfluenceUpload.objects.get(pk=confluence_upload_id)
    except ConfluenceUpload.DoesNotExist:
        print(f"[Importer Task] CRITICAL: ConfluenceUpload record {confluence_upload_id} not found. Aborting.")
        return f"ConfluenceUpload record {confluence_upload_id} not found."

    # Initialize/Reset progress fields for this run
    upload_record.status = ConfluenceUpload.STATUS_PROCESSING
    upload_record.task_id = self.request.id
    upload_record.pages_succeeded_count = 0
    upload_record.pages_failed_count = 0
    upload_record.attachments_succeeded_count = 0
    upload_record.progress_message = "Import process initiated..."
    upload_record.error_details = ""
    upload_record.save(update_fields=['status', 'task_id', 'pages_succeeded_count', 'pages_failed_count', 'attachments_succeeded_count', 'progress_message', 'error_details'])

    importer_user = upload_record.user
    print(f"[Importer Task] ID {self.request.id} | Starting import for Upload ID: {confluence_upload_id} by User: {importer_user.username if importer_user else 'Unknown'}")
    zip_file_actual_path = upload_record.file.path

    if not os.path.exists(zip_file_actual_path):
        error_message = f"Uploaded ZIP file not found: {zip_file_actual_path} for Upload ID {confluence_upload_id}."
        upload_record.status = ConfluenceUpload.STATUS_FAILED
        upload_record.progress_message = "Error: ZIP file not found."
        upload_record.error_details = error_message
        upload_record.save()
        return error_message

    temp_extraction_main_dir = f"temp_confluence_export_{self.request.id}"
    abs_temp_extraction_main_dir = os.path.join(os.getcwd(), temp_extraction_main_dir)

    target_workspace_for_import = None
    target_space_for_pages = None

    if upload_record.target_space:
        target_space_for_pages = upload_record.target_space
        if hasattr(target_space_for_pages, 'workspace') and target_space_for_pages.workspace:
            target_workspace_for_import = target_space_for_pages.workspace
            upload_record.progress_message = f"Targeting specified Space: '{target_space_for_pages.name}' in Workspace '{target_workspace_for_import.name}'."
        else:
            target_workspace_for_import = None
            upload_record.progress_message = f"Targeting specified Space: '{target_space_for_pages.name}' but its Workspace is not set."
    elif upload_record.target_workspace:
        target_workspace_for_import = upload_record.target_workspace
        upload_record.progress_message = f"Targeting specified Workspace: '{target_workspace_for_import.name}'. Attempting to use first available Space."
        if Space and target_workspace_for_import:
            target_space_for_pages = Space.objects.filter(workspace=target_workspace_for_import, is_deleted=False).first()
            if target_space_for_pages:
                upload_record.progress_message += f" Using Space: '{target_space_for_pages.name}'."
            else:
                upload_record.progress_message += " No non-deleted Spaces found in target Workspace."
        elif not Space:
             upload_record.progress_message += " Space model not available."
    else:
        upload_record.progress_message = "No specific target. Using system default."
        if Workspace:
            target_workspace_for_import = Workspace.objects.filter(is_deleted=False).first()
            if target_workspace_for_import and Space:
                target_space_for_pages = Space.objects.filter(workspace=target_workspace_for_import, is_deleted=False).first()
                if target_space_for_pages:
                    upload_record.progress_message += f" Using fallback Space: '{target_space_for_pages.name}' in Workspace '{target_workspace_for_import.name}'."
                else:
                    upload_record.progress_message += f" Fallback Workspace '{target_workspace_for_import.name}' has no non-deleted Spaces."
            elif not target_workspace_for_import:
                 upload_record.progress_message += " No non-deleted fallback Workspace found."
        else:
            upload_record.progress_message += " Workspace model not available for fallback."
    upload_record.save(update_fields=['progress_message'])
    print(f"  {upload_record.progress_message}")


    if not target_space_for_pages:
        error_msg_no_space = "Import failed: No target Space could be determined. Please specify a target or ensure a default/fallback space exists and is not deleted."
        print(f"[Importer Task] ID {self.request.id} | {error_msg_no_space}")
        upload_record.status = ConfluenceUpload.STATUS_FAILED
        upload_record.progress_message = error_msg_no_space
        upload_record.error_details = error_msg_no_space
        # Save handled in finally
        raise Exception(error_msg_no_space) # Go to finally for cleanup and save

    original_id_to_new_pk_map = {}

    try:
        upload_record.progress_message = "Extracting files from ZIP archive...";
        upload_record.save(update_fields=['progress_message'])
        html_files, metadata_file_path = extract_html_and_metadata_from_zip(
            zip_file_actual_path, temp_extract_dir=abs_temp_extraction_main_dir
        )
        upload_record.progress_message = "File extraction complete.";
        upload_record.save(update_fields=['progress_message'])

        page_hierarchy_from_metadata = []
        if metadata_file_path:
            upload_record.progress_message = "Parsing metadata file (e.g., entities.xml)...";
            upload_record.save(update_fields=['progress_message'])
            page_hierarchy_from_metadata = parse_confluence_metadata_for_hierarchy(metadata_file_path)
            if not page_hierarchy_from_metadata:
                error_list_for_details.append(f"Metadata file '{os.path.basename(metadata_file_path)}' was parsed but yielded no page hierarchy data.")
        else:
            final_task_message = "Import failed: Metadata file (e.g., entities.xml) missing from ZIP."
            error_list_for_details.append(final_task_message)
            raise Exception(final_task_message)

        html_id_to_path_map = {}
        parsed_title_to_html_path = {}
        if html_files:
            upload_record.progress_message = f"Indexing {len(html_files)} HTML files...";
            upload_record.save(update_fields=['progress_message'])
            for html_path_for_map in html_files:
                temp_parsed_data = parse_html_file_basic(html_path_for_map)
                if temp_parsed_data and not temp_parsed_data.get("error"):
                    html_extracted_id = temp_parsed_data.get("html_extracted_page_id")
                    if html_extracted_id:
                        if html_extracted_id in html_id_to_path_map:
                            msg = f"Duplicate embedded Page ID '{html_extracted_id}'. HTML '{os.path.basename(html_path_for_map)}' vs '{os.path.basename(html_id_to_path_map[html_extracted_id])}'."
                            print(f"  WARNING: {msg}"); error_list_for_details.append(msg)
                        else: html_id_to_path_map[html_extracted_id] = html_path_for_map
                    parsed_title = temp_parsed_data.get("title")
                    if parsed_title:
                        if parsed_title in parsed_title_to_html_path and parsed_title_to_html_path[parsed_title] != html_path_for_map :
                            msg = f"Duplicate HTML title '{parsed_title}' maps to multiple files. Title map uses first: '{os.path.basename(parsed_title_to_html_path[parsed_title])}'."
                            print(f"  WARNING: {msg}"); # Not adding to main error_details, just a parsing ambiguity
                        elif parsed_title not in parsed_title_to_html_path:
                             parsed_title_to_html_path[parsed_title] = html_path_for_map
                elif temp_parsed_data and temp_parsed_data.get("error"):
                     error_list_for_details.append(f"Skipping file '{os.path.basename(html_path_for_map)}' from map creation due to parsing error: {temp_parsed_data.get('error')}")
            upload_record.progress_message = f"HTML indexing complete. Found {len(html_id_to_path_map)} embedded IDs, {len(parsed_title_to_html_path)} titles.";
            upload_record.save(update_fields=['progress_message'])
        else:
            final_task_message = "Import failed: No HTML files found in ZIP."
            error_list_for_details.append(final_task_message)
            raise Exception(final_task_message)

        if not page_hierarchy_from_metadata:
            final_task_message = "Import failed: Page metadata missing or empty, cannot proceed."
            error_list_for_details.append(final_task_message)
            raise Exception(final_task_message)

        num_metadata_pages = len(page_hierarchy_from_metadata)
        print(f"[Importer Task] ID {self.request.id} | Processing {num_metadata_pages} pages from metadata into Space '{target_space_for_pages.name}' (ID: {target_space_for_pages.id})")

        for i, page_meta_entry in enumerate(page_hierarchy_from_metadata):
            authoritative_page_id = page_meta_entry.get('id')
            authoritative_page_title = page_meta_entry.get('title', f"Untitled Page {authoritative_page_id or 'UnknownID'}")
            log_page_ref = f"'{authoritative_page_title}' (Metadata ID: {authoritative_page_id})"

            if i % 5 == 0 or i == num_metadata_pages - 1:
                upload_record.progress_message = f"Processing page {i+1}/{num_metadata_pages}: {log_page_ref}..."
                upload_record.pages_succeeded_count = local_pages_succeeded_count
                upload_record.pages_failed_count = local_pages_failed_count
                upload_record.attachments_succeeded_count = local_attachments_succeeded_count
                upload_record.save(update_fields=['progress_message', 'pages_succeeded_count', 'pages_failed_count', 'attachments_succeeded_count'])

            if not authoritative_page_id:
                msg = f"Metadata entry {i+1} missing ID. Entry: {page_meta_entry}. Skipping."
                print(f"  WARNING: {msg}"); error_list_for_details.append(msg)
                local_pages_failed_count += 1
                continue

            html_path = None; match_type = "No Match"
            if authoritative_page_id in html_id_to_path_map:
                html_path = html_id_to_path_map[authoritative_page_id]
                match_type = "HTML Embedded ID"
            elif authoritative_page_title in parsed_title_to_html_path:
                html_path = parsed_title_to_html_path[authoritative_page_title]
                match_type = "HTML Title"
                msg = f"HTML for {log_page_ref} not found by embedded ID. Matched by title using '{authoritative_page_title}': {os.path.basename(html_path)}."
                print(f"    WARNING: {msg}"); # Log this, but don't add to main error_details unless page creation fails

            if not html_path:
                msg = f"HTML file for page {log_page_ref} not found by ID or title match. Skipping page."
                print(f"    ERROR: {msg}"); error_list_for_details.append(msg)
                local_pages_failed_count += 1
                continue

            parsed_page_html_data = parse_html_file_basic(html_path)
            if not parsed_page_html_data or parsed_page_html_data.get("error") or not parsed_page_html_data.get("main_content_html"):
                error_detail = parsed_page_html_data.get('error', 'No main content') if parsed_page_html_data else 'Parsing failed'
                msg = f"Failed to parse main content from HTML file '{os.path.basename(html_path)}' for page {log_page_ref} (match type: {match_type}). Error: {error_detail}. Skipping page."
                print(f"    WARNING: {msg}"); error_list_for_details.append(msg)
                local_pages_failed_count += 1
                continue

            main_content_html = parsed_page_html_data.get("main_content_html")
            content_json = convert_html_to_prosemirror_json(main_content_html)

            if Page.objects.filter(original_confluence_id=authoritative_page_id, space=target_space_for_pages).exists():
                msg = f"Page '{authoritative_page_title}' (OrigID: {authoritative_page_id}) already exists in target space '{target_space_for_pages.name}'. Skipping."
                print(f"    {msg}"); # Not necessarily an error for error_details, but a skip.
                local_pages_failed_count += 1 # Count as failed/skipped for progress
                continue
            try:
                created_page_object = Page.objects.create(title=authoritative_page_title, content_json=content_json, space=target_space_for_pages, imported_by=importer_user, original_confluence_id=authoritative_page_id)
                local_pages_succeeded_count += 1
                if authoritative_page_id: original_id_to_new_pk_map[authoritative_page_id] = created_page_object.pk

                referenced_attachments_in_html = parsed_page_html_data.get("referenced_attachments", [])
                attachments_created_count_for_page = 0
                if referenced_attachments_in_html:
                    for attachment_ref_name in referenced_attachments_in_html:
                        # ... (attachment finding logic - as before) ...
                        # On success: local_attachments_succeeded_count += 1
                        # On failure: error_list_for_details.append(...)
                        potential_paths_to_try = [os.path.join(os.path.dirname(html_path), attachment_ref_name), os.path.join(os.path.dirname(html_path), "attachments", attachment_ref_name), os.path.join(abs_temp_extraction_main_dir, "attachments", attachment_ref_name), os.path.join(abs_temp_extraction_main_dir, attachment_ref_name)]
                        attachment_file_path_found = next((p for p in potential_paths_to_try if os.path.exists(p) and os.path.isfile(p)), None)
                        if attachment_file_path_found:
                            try:
                                mime_type_guess, _ = mimetypes.guess_type(attachment_file_path_found)
                                with open(attachment_file_path_found, 'rb') as f_attach:
                                    django_file = File(f_attach, name=os.path.basename(attachment_ref_name))
                                    Attachment.objects.create(page=created_page_object, original_filename=os.path.basename(attachment_ref_name), file=django_file, mime_type=mime_type_guess or 'application/octet-stream', imported_by=importer_user)
                                local_attachments_succeeded_count += 1; attachments_created_count_for_page+=1
                            except Exception as attach_create_error: error_list_for_details.append(f"Attachment '{attachment_ref_name}' for {log_page_ref}: Create error {attach_create_error}")
                        else: error_list_for_details.append(f"Attachment '{attachment_ref_name}' for {log_page_ref}: File not found.")
                if attachments_created_count_for_page > 0 and created_page_object.content_json and 'content' in created_page_object.content_json:
                    page_attachments_for_resolve = Attachment.objects.filter(page=created_page_object)
                    attachments_by_filename_map = {att.original_filename: att.file.url for att in page_attachments_for_resolve if att.file and hasattr(att.file, 'url')}
                    if attachments_by_filename_map: _resolve_symbolic_image_srcs(created_page_object.content_json['content'], attachments_by_filename_map); created_page_object.save(update_fields=['content_json', 'updated_at'])
            except Exception as page_create_error:
                local_pages_failed_count += 1
                msg = f"Page {log_page_ref}: DB creation error: {page_create_error}"
                print(f"    ERROR: {msg}"); error_list_for_details.append(msg)

        upload_record.pages_succeeded_count = local_pages_succeeded_count
        upload_record.pages_failed_count = local_pages_failed_count
        upload_record.attachments_succeeded_count = local_attachments_succeeded_count
        upload_record.save(update_fields=['pages_succeeded_count', 'pages_failed_count', 'attachments_succeeded_count'])

        if page_hierarchy_from_metadata and original_id_to_new_pk_map:
            upload_record.progress_message = "Linking page hierarchy..."; upload_record.save(update_fields=['progress_message'])
            # ... (Hierarchy linking - as before, no direct count changes on upload_record here) ...
            for page_meta_entry_for_link in page_hierarchy_from_metadata:
                original_child_id = page_meta_entry_for_link.get('id'); original_parent_id = page_meta_entry_for_link.get('parent_id')
                if original_child_id and original_parent_id:
                    child_pk, parent_pk = original_id_to_new_pk_map.get(original_child_id), original_id_to_new_pk_map.get(original_parent_id)
                    if child_pk and parent_pk:
                        try:
                            child_page = Page.objects.get(pk=child_pk)
                            if child_page.parent_id == parent_pk: continue
                            parent_page_instance = Page.objects.get(pk=parent_pk)
                            child_page.parent = parent_page_instance; child_page.save(update_fields=['parent', 'updated_at']); pages_linked_count += 1
                        except Page.DoesNotExist: error_list_for_details.append(f"Hierarchy link failed: Child (PK:{child_pk}) or Parent (PK:{parent_pk}) not found.")
                        except Exception as link_error: error_list_for_details.append(f"Hierarchy link error OrigID {original_child_id} to {original_parent_id}: {link_error}")
            upload_record.progress_message = f"Hierarchy linking complete. {pages_linked_count} links established."; upload_record.save(update_fields=['progress_message'])

        if upload_record.pages_succeeded_count > 0:
            upload_record.status = ConfluenceUpload.STATUS_COMPLETED
            upload_record.progress_message = f"Import completed. Pages: {upload_record.pages_succeeded_count} succeeded, {upload_record.pages_failed_count} failed. Attachments: {upload_record.attachments_succeeded_count}. Pages linked: {pages_linked_count}."
        elif upload_record.pages_failed_count > 0 and num_metadata_pages > 0:
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            upload_record.progress_message = f"Import failed. Pages: {upload_record.pages_succeeded_count} succeeded, {upload_record.pages_failed_count} failed. Attachments: {upload_record.attachments_succeeded_count}. Pages linked: {pages_linked_count}."
        else:
            if upload_record.status != ConfluenceUpload.STATUS_FAILED:
                upload_record.status = ConfluenceUpload.STATUS_COMPLETED # Or FAILED if 0 pages created from metadata is a failure
            upload_record.progress_message = f"Import finished. Pages created: {upload_record.pages_succeeded_count}, Failed/Skipped: {upload_record.pages_failed_count}, Attachments: {upload_record.attachments_succeeded_count}, Linked: {pages_linked_count}. Check logs for details."

        if error_list_for_details:
            # Prepend to existing error_details if any, rather than overwriting
            existing_error_details = upload_record.error_details if upload_record.error_details else ""
            new_errors = "\n".join(error_list_for_details)
            full_error_message = f"{existing_error_details}\n{new_errors}".strip()
            upload_record.error_details = full_error_message[:2000] # Limit length

    except Exception as e:
        error_message_critical = f"CRITICAL ERROR: {type(e).__name__} - {e}"
        print(f"[Importer Task] ID {self.request.id} | {error_message_critical}")
        # Ensure upload_record is available and update its fields
        if upload_record: # Check if upload_record was successfully fetched
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            upload_record.progress_message = "Import failed due to a critical error."

            current_errors = error_list_for_details if error_list_for_details else []
            current_errors.insert(0, error_message_critical)

            # Prepend to existing error_details if any
            existing_error_details = upload_record.error_details if upload_record.error_details and upload_record.error_details != error_message_critical else ""
            new_error_string = "\n".join(current_errors)
            full_error_message = f"{existing_error_details}\n{new_error_string}".strip()
            if error_message_critical in existing_error_details and error_message_critical in new_error_string: # Avoid duplication if already set
                 full_error_message = existing_error_details if existing_error_details else new_error_string

            upload_record.error_details = full_error_message[:2000]
        # final_task_message is already set to error_message_critical by this point in original logic.
        # No need to re-assign if it's already capturing the core error.

    finally:
        # Ensure upload_record is saved if it exists
        if upload_record:
            upload_record.save()

        if os.path.exists(abs_temp_extraction_main_dir):
            cleanup_temp_extraction_dir(temp_extract_dir=abs_temp_extraction_main_dir)
        print(f"[Importer Task] ID {self.request.id} | Finished. Final status: {upload_record.get_status_display()}. Message: {upload_record.progress_message}")

    return upload_record.progress_message
