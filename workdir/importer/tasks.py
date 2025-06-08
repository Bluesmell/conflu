from celery import shared_task
import os
import re
import shutil
import mimetypes # For attachment processing

from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic, parse_confluence_metadata_for_hierarchy
from .models import ConfluenceUpload
from .converter import convert_html_to_prosemirror_json

from django.contrib.auth import get_user_model
from pages.models import Page, Attachment
from django.core.files import File # For creating Django File objects for attachments

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
    try:
        upload_record = ConfluenceUpload.objects.get(pk=confluence_upload_id)
    except ConfluenceUpload.DoesNotExist:
        print(f"[Importer Task] CRITICAL: ConfluenceUpload record {confluence_upload_id} not found. Aborting.")
        return f"ConfluenceUpload record {confluence_upload_id} not found."

    upload_record.status = ConfluenceUpload.STATUS_PROCESSING
    upload_record.task_id = self.request.id
    upload_record.save()

    importer_user = upload_record.user
    print(f"[Importer Task] ID {self.request.id} | Starting import for Upload ID: {confluence_upload_id} by User: {importer_user.username if importer_user else 'Unknown'}")
    zip_file_actual_path = upload_record.file.path

    if not os.path.exists(zip_file_actual_path):
        error_message = f"Uploaded ZIP file not found: {zip_file_actual_path} for Upload ID {confluence_upload_id}."
        upload_record.status = ConfluenceUpload.STATUS_FAILED; upload_record.save()
        return error_message

    temp_extraction_main_dir = f"temp_confluence_export_{self.request.id}"
    abs_temp_extraction_main_dir = os.path.join(os.getcwd(), temp_extraction_main_dir)

    default_workspace = None
    target_space_for_pages = None
    if Workspace:
        default_workspace = Workspace.objects.first()
        if default_workspace and Space:
            target_space_for_pages = Space.objects.filter(workspace=default_workspace).first()
            if not target_space_for_pages:
                print(f"[Importer Task] ID {self.request.id} | WARNING: No Space found in default workspace '{default_workspace.name}'. Page creation may fail if Space is mandatory.")
        elif not default_workspace:
             print(f"[Importer Task] ID {self.request.id} | WARNING: No default workspace found.")
    else:
        print(f"[Importer Task] ID {self.request.id} | WARNING: Workspace model not available.")

    # Page model requires space, so if target_space_for_pages is None, creation will fail.
    if not target_space_for_pages and Space:
        print(f"[Importer Task] ID {self.request.id} | CRITICAL: No target Space available for page import. Aborting as Page model requires a Space.")
        upload_record.status = ConfluenceUpload.STATUS_FAILED
        upload_record.save()
        cleanup_temp_extraction_dir(temp_extract_dir=abs_temp_extraction_main_dir) # Cleanup before early exit
        return "No target Space available for import. Page model requires a Space."

    pages_created_count = 0
    pages_failed_count = 0
    attachments_processed_total = 0
    pages_linked_count = 0 # Initialize for hierarchy linking
    original_id_to_new_pk_map = {}

    final_task_message = f"Import task for Upload ID {confluence_upload_id} processing."

    try:
        html_files, metadata_file_path = extract_html_and_metadata_from_zip(
            zip_file_actual_path, temp_extract_dir=abs_temp_extraction_main_dir
        )

        page_hierarchy_from_metadata = []
        if metadata_file_path:
            print(f"[Importer Task] ID {self.request.id} | Parsing metadata file for hierarchy: {metadata_file_path}")
            page_hierarchy_from_metadata = parse_confluence_metadata_for_hierarchy(metadata_file_path)
            if page_hierarchy_from_metadata:
                print(f"  Found {len(page_hierarchy_from_metadata)} page entries in metadata.")
            else: # Metadata file found but no page data extracted
                print(f"  WARNING: Metadata file '{metadata_file_path}' was parsed but yielded no page hierarchy data.")
                # This is treated as a failure condition below if it's the only source of pages.
        else: # No metadata file found in the zip
            print(f"[Importer Task] ID {self.request.id} | CRITICAL: Metadata file (e.g., entities.xml) missing from ZIP. Cannot reliably import pages or hierarchy.")
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            final_task_message = "Import failed: Metadata file (e.g., entities.xml) missing from ZIP."
            # Save and return early are handled in finally block
            raise Exception(final_task_message) # Raise to go to finally block for cleanup

        parsed_title_to_html_path = {}
        if html_files:
            print(f"[Importer Task] ID {self.request.id} | Indexing {len(html_files)} HTML files by title...")
            for html_path_for_map in html_files:
                temp_parsed_data = parse_html_file_basic(html_path_for_map)
                if temp_parsed_data and temp_parsed_data.get("title"):
                    parsed_title = temp_parsed_data["title"]
                    if parsed_title in parsed_title_to_html_path:
                        print(f"  WARNING: Duplicate HTML title '{parsed_title}'. Using first: {parsed_title_to_html_path[parsed_title]}. Skipping {html_path_for_map}.")
                    else:
                        parsed_title_to_html_path[parsed_title] = html_path_for_map
            print(f"  Finished indexing HTML files. Found {len(parsed_title_to_html_path)} unique titles.")
        else:
            print(f"[Importer Task] ID {self.request.id} | CRITICAL: No HTML files found in ZIP.")
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            final_task_message = "Import failed: No HTML files found in ZIP."
            raise Exception(final_task_message)

        if not page_hierarchy_from_metadata:
            print(f"[Importer Task] ID {self.request.id} | CRITICAL: No page data parsed from metadata. Cannot proceed with metadata-driven import.")
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            final_task_message = "Import failed: Page metadata missing or empty, cannot map HTML files to pages."
            raise Exception(final_task_message)

        print(f"[Importer Task] ID {self.request.id} | Processing {len(page_hierarchy_from_metadata)} pages based on metadata entries...")
        for i, page_meta_entry in enumerate(page_hierarchy_from_metadata):
            authoritative_page_id = page_meta_entry.get('id')
            authoritative_page_title = page_meta_entry.get('title')

            if not authoritative_page_id or not authoritative_page_title:
                print(f"  WARNING: Metadata entry missing ID or Title. Entry: {page_meta_entry}. Skipping.")
                pages_failed_count += 1
                continue

            print(f"  Processing metadata entry ({i+1}/{len(page_hierarchy_from_metadata)}): ID='{authoritative_page_id}', Title='{authoritative_page_title}'")

            html_path = parsed_title_to_html_path.get(authoritative_page_title)
            if not html_path:
                print(f"    WARNING: HTML file for page '{authoritative_page_title}' (ID: {authoritative_page_id}) not found by title match. Skipping page.")
                pages_failed_count += 1
                continue

            parsed_page_html_data = parse_html_file_basic(html_path)
            if not parsed_page_html_data or parsed_page_html_data.get("error") or not parsed_page_html_data.get("main_content_html"):
                error_detail = parsed_page_html_data.get("error", "no main_content_html") if parsed_page_html_data else "parser returned None"
                print(f"    WARNING: Failed to parse main content from HTML file '{html_path}' for page '{authoritative_page_title}'. Error: {error_detail}. Skipping page.")
                pages_failed_count += 1
                continue

            main_content_html = parsed_page_html_data.get("main_content_html")
            referenced_attachments_in_html = parsed_page_html_data.get("referenced_attachments", [])
            content_json = convert_html_to_prosemirror_json(main_content_html)

            if Page.objects.filter(original_confluence_id=authoritative_page_id, space=target_space_for_pages).exists():
                print(f"    Page '{authoritative_page_title}' (OrigID: {authoritative_page_id}) already exists in target space. Skipping.")
                pages_failed_count += 1
                continue

            created_page_object = None
            try:
                created_page_object = Page.objects.create(
                    title=authoritative_page_title,
                    content_json=content_json,
                    space=target_space_for_pages,
                    imported_by=importer_user,
                    original_confluence_id=authoritative_page_id
                )
                pages_created_count += 1
                original_id_to_new_pk_map[authoritative_page_id] = created_page_object.pk
                print(f"    Successfully created Page: '{created_page_object.title}' (DB ID: {created_page_object.pk})")

                attachments_created_count_for_page = 0
                if referenced_attachments_in_html:
                    print(f"      Found {len(referenced_attachments_in_html)} referenced attachments. Processing...")
                    for attachment_ref_name in referenced_attachments_in_html:
                        # Construct search paths relative to HTML file's dir and global attachments dir
                        # html_path is absolute path to the current HTML file being processed
                        # abs_temp_extraction_main_dir is absolute path to the root of extracted ZIP
                        potential_paths_to_try = [
                            os.path.join(os.path.dirname(html_path), attachment_ref_name), # Relative to HTML file
                            os.path.join(os.path.dirname(html_path), "attachments", attachment_ref_name), # In 'attachments' subdir relative to HTML
                            os.path.join(abs_temp_extraction_main_dir, "attachments", attachment_ref_name), # Global 'attachments' folder
                            os.path.join(abs_temp_extraction_main_dir, attachment_ref_name), # In root of ZIP
                        ]
                        attachment_file_path_found = None
                        for p_path in potential_paths_to_try:
                            if os.path.exists(p_path) and os.path.isfile(p_path):
                                attachment_file_path_found = p_path
                                break

                        if attachment_file_path_found:
                            try:
                                mime_type_guess, _ = mimetypes.guess_type(attachment_file_path_found)
                                with open(attachment_file_path_found, 'rb') as f_attach:
                                    django_file = File(f_attach, name=os.path.basename(attachment_ref_name))
                                    Attachment.objects.create(
                                        page=created_page_object,
                                        original_filename=os.path.basename(attachment_ref_name),
                                        file=django_file,
                                        mime_type=mime_type_guess if mime_type_guess else 'application/octet-stream',
                                        imported_by=importer_user
                                    )
                                attachments_created_count_for_page += 1
                            except Exception as attach_create_error:
                                print(f"      ERROR creating Attachment record for '{attachment_ref_name}': {attach_create_error}")
                        else:
                            print(f"      WARNING: Could not locate attachment file '{attachment_ref_name}'.")
                    if attachments_created_count_for_page > 0:
                        attachments_processed_total += attachments_created_count_for_page
                        print(f"      Processed {attachments_created_count_for_page} attachments for this page.")

                if created_page_object.content_json and 'content' in created_page_object.content_json and attachments_created_count_for_page > 0:
                    page_attachments_for_resolve = Attachment.objects.filter(page=created_page_object)
                    attachments_by_filename_map = {
                        att.original_filename: att.file.url for att in page_attachments_for_resolve if att.file and hasattr(att.file, 'url')
                    }
                    if attachments_by_filename_map:
                        print(f"      Resolving symbolic image srcs for page '{created_page_object.title}'...")
                        _resolve_symbolic_image_srcs(created_page_object.content_json['content'], attachments_by_filename_map)
                        created_page_object.save(update_fields=['content_json', 'updated_at'])
                        print(f"      Finished resolving image srcs.")

            except Exception as page_create_error:
                pages_failed_count += 1
                print(f"    ERROR creating page '{authoritative_page_title}' (OrigID: {authoritative_page_id}) or its assets: {page_create_error}")

        if page_hierarchy_from_metadata and original_id_to_new_pk_map:
            print(f"[Importer Task] ID {self.request.id} | Starting Pass 2: Linking page hierarchy...")
            for page_meta_entry_for_link in page_hierarchy_from_metadata:
                original_child_id = page_meta_entry_for_link.get('id')
                original_parent_id = page_meta_entry_for_link.get('parent_id')
                if original_child_id and original_parent_id:
                    child_pk = original_id_to_new_pk_map.get(original_child_id)
                    parent_pk = original_id_to_new_pk_map.get(original_parent_id)
                    if child_pk and parent_pk:
                        try:
                            child_page = Page.objects.get(pk=child_pk)
                            if child_page.parent_id == parent_pk: continue
                            parent_page_instance = Page.objects.get(pk=parent_pk)
                            child_page.parent = parent_page_instance
                            child_page.save(update_fields=['parent', 'updated_at'])
                            pages_linked_count += 1
                        except Page.DoesNotExist: print(f"  WARNING: Child (PK:{child_pk}) or Parent (PK:{parent_pk}) not found for linking.")
                        except Exception as link_error: print(f"  ERROR linking OrigID {original_child_id} to {original_parent_id}: {link_error}")
            print(f"  Successfully linked {pages_linked_count} pages in hierarchy.")

        if pages_created_count > 0:
            upload_record.status = ConfluenceUpload.STATUS_COMPLETED
            final_task_message = f"Import completed. Pages created: {pages_created_count}. Pages failed/skipped: {pages_failed_count}. Attachments processed: {attachments_processed_total}. Pages linked: {pages_linked_count}."
        elif pages_failed_count > 0 :
            upload_record.status = ConfluenceUpload.STATUS_FAILED
            final_task_message = f"Import failed. Pages created: 0. Pages failed/skipped: {pages_failed_count}."
        else: # No pages in metadata matched, or other earlier critical failure.
            upload_record.status = upload_record.status if upload_record.status == ConfluenceUpload.STATUS_FAILED else ConfluenceUpload.STATUS_COMPLETED
            # If already failed, keep failed. Otherwise, could be completed if no pages were expected.
            # The logic above for missing metadata/HTML should set to FAILED.
            final_task_message = final_task_message if upload_record.status == ConfluenceUpload.STATUS_FAILED else \
                                 "Import finished: No new pages were imported. Check logs for details (e.g., all pages existed, or no matching HTML for metadata)."


    except Exception as e:
        error_message_critical = f"CRITICAL ERROR during import for Upload ID {confluence_upload_id}: {type(e).__name__} - {e}"
        print(f"[Importer Task] ID {self.request.id} | {error_message_critical}")
        # Check if upload_record was fetched before trying to update it
        if 'upload_record' in locals() and isinstance(upload_record, ConfluenceUpload):
            upload_record.status = ConfluenceUpload.STATUS_FAILED
        final_task_message = error_message_critical
    finally:
        if 'upload_record' in locals() and isinstance(upload_record, ConfluenceUpload):
             upload_record.save()
        if os.path.exists(abs_temp_extraction_main_dir): # Check before cleaning
            cleanup_temp_extraction_dir(temp_extract_dir=abs_temp_extraction_main_dir)

        final_status_to_log = 'Unknown (upload_record not initialized)'
        if 'upload_record' in locals() and isinstance(upload_record, ConfluenceUpload):
            final_status_to_log = upload_record.get_status_display()

        print(f"[Importer Task] ID {self.request.id} | Finished processing for Upload ID: {confluence_upload_id}. Final status: {final_status_to_log}")

    return final_task_message
