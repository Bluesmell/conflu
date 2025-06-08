
from celery import shared_task
import os
import re # For extracting page ID from filename
import shutil
import zipfile # Keep for context

from celery import shared_task

from .utils import extract_html_and_metadata_from_zip, cleanup_temp_extraction_dir
from .parser import parse_html_file_basic, parse_confluence_metadata_for_hierarchy # Added new parser
from .models import ConfluenceUpload
from .converter import convert_html_to_prosemirror_json

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

# Helper function for resolving image srcs in ProseMirror content
def _resolve_symbolic_image_srcs(node_list, attachments_by_filename):
    """
    Recursively traverses a list of ProseMirror nodes (like a 'content' array),
    finds image nodes with symbolic 'pm:attachment:' src, and replaces them
    with actual attachment URLs.
    Modifies node_list in-place.
    """
    if not isinstance(node_list, list):
        return

    for node in node_list:
        if not isinstance(node, dict):
            continue

        if node.get("type") == "image":
            attrs = node.get("attrs", {})
            src = attrs.get("src", "")
            if src.startswith("pm:attachment:"):
                filename = src.replace("pm:attachment:", "", 1)
                if filename in attachments_by_filename:
                    attrs["src"] = attachments_by_filename[filename]
                    # print(f"    Resolved image src for '{filename}' to '{attrs['src']}'")
                else:
                    print(f"    WARNING: Image attachment '{filename}' referenced in content but not found for page. Symbolic src will remain.")

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
            return final_task_message

        # --- Parse Metadata for Hierarchy (Early Pass) ---
        page_hierarchy_from_metadata = []
        if metadata_file:
            print(f"[Importer Task] ID {self.request.id} | Parsing metadata file for hierarchy: {metadata_file}")
            page_hierarchy_from_metadata = parse_confluence_metadata_for_hierarchy(metadata_file)
            if page_hierarchy_from_metadata:
                print(f"  Found {len(page_hierarchy_from_metadata)} page entries in metadata.")
            else:
                print(f"  No hierarchy data extracted from metadata file or file was empty/invalid.")
        else:
            print(f"[Importer Task] ID {self.request.id} | No metadata file found, cannot process page hierarchy from it.")

        original_id_to_new_pk_map = {} # To map original Confluence IDs to new Page PKs

        # --- Pass 1: Loop through all HTML files, create pages ---
        for i, html_path in enumerate(html_files):
            print(f"[Importer Task] ID {self.request.id} | Processing HTML file ({i+1}/{len(html_files)}): {html_path}")

            parsed_page_data = parse_html_file_basic(html_path)

            if not parsed_page_data or parsed_page_data.get("error"):
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
                    # parent field will be set in Pass 2
                )
                pages_created_count += 1
                print(f"  Successfully created Page: '{created_page_object.title}' in Space '{target_space.name}' (ID: {created_page_object.id}, OrigID: {original_confluence_page_id})")

                if created_page_object.original_confluence_id:
                    original_id_to_new_pk_map[created_page_object.original_confluence_id] = created_page_object.pk

                # --- Attachment Processing (remains from Part 2 subtask) ---
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

                # --- Post-process Page Content for Image Src Resolution ---
                if created_page_object.content_json and 'content' in created_page_object.content_json:
                    page_attachments = Attachment.objects.filter(page=created_page_object)
                    attachments_by_filename_map = {
                        att.original_filename: att.file.url
                        for att in page_attachments if att.file and hasattr(att.file, 'url') # Ensure file exists and has URL
                    }

                    if attachments_by_filename_map:
                        print(f"    Resolving symbolic image srcs for page '{created_page_object.title}'...")
                        _resolve_symbolic_image_srcs(created_page_object.content_json['content'], attachments_by_filename_map)
                        created_page_object.save(update_fields=['content_json', 'updated_at'])
                        print(f"    Finished resolving image srcs. Page content_json updated.")

            except Exception as page_create_error: # This except handles errors from Page.objects.create or attachment/image processing for that page
                pages_failed_count += 1
                print(f"[Importer Task] ID {self.request.id} | ERROR processing page '{page_title}' or its attachments/images: {page_create_error}")

        # --- Pass 2: Link page hierarchy ---
        if page_hierarchy_from_metadata and original_id_to_new_pk_map:
            print(f"[Importer Task] ID {self.request.id} | Starting Pass 2: Linking page hierarchy...")
            pages_linked_count = 0
            for page_meta_entry in page_hierarchy_from_metadata:
                original_child_id = page_meta_entry.get('id')
                original_parent_id = page_meta_entry.get('parent_id')

                if original_child_id and original_parent_id:
                    child_pk = original_id_to_new_pk_map.get(original_child_id)
                    parent_pk = original_id_to_new_pk_map.get(original_parent_id)

                    if child_pk and parent_pk:
                        try:
                            child_page = Page.objects.get(pk=child_pk)
                            # Check if parent was already set (e.g. task retry with partial completion)
                            if child_page.parent_id == parent_pk:
                                print(f"  Hierarchy for {child_page.title} (OrigID: {original_child_id}) to parent (OrigID: {original_parent_id}) already set.")
                                continue

                            parent_page_instance = Page.objects.get(pk=parent_pk)
                            child_page.parent = parent_page_instance
                            child_page.save()
                            pages_linked_count += 1
                            # print(f"  Linked page '{child_page.title}' (OrigID: {original_child_id}) to parent '{parent_page_instance.title}' (OrigID: {original_parent_id})")
                        except Page.DoesNotExist:
                            print(f"  WARNING: Could not find child (PK:{child_pk}) or parent (PK:{parent_pk}) page in database for linking. OrigChildID: {original_child_id}, OrigParentID: {original_parent_id}")
                        except Exception as link_error:
                            print(f"  ERROR linking page OrigID {original_child_id} to parent OrigID {original_parent_id}: {link_error}")

            if pages_linked_count > 0:
                print(f"  Successfully linked {pages_linked_count} pages in hierarchy.")
            else:
                print(f"  No new page hierarchy links were established in Pass 2.")
        elif not page_hierarchy_from_metadata:
            print(f"[Importer Task] ID {self.request.id} | No metadata for hierarchy, skipping Pass 2 for linking.")
        elif not original_id_to_new_pk_map: # No pages created had original IDs, or no pages created at all
            print(f"[Importer Task] ID {self.request.id} | No pages mapped with original IDs, skipping Pass 2 for linking.")


        # Determine final status based on outcomes
        if pages_created_count > 0: # If any page was created, consider it completed, even if some failed or hierarchy failed.
            upload_record.status = ConfluenceUpload.STATUS_COMPLETED
        elif not html_files: # No HTML files to process (status already set by that block)
            pass
        else: # No pages created, and there were HTML files to process (all failed or were skipped)
             upload_record.status = ConfluenceUpload.STATUS_FAILED

        final_task_message = (f"Import task for Upload ID {confluence_upload_id} finished. "
                              f"Pages created: {pages_created_count}. Pages failed/skipped: {pages_failed_count}. "
                              f"Pages linked in hierarchy: {pages_linked_count if 'pages_linked_count' in locals() else 0}.") # Add link count
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
