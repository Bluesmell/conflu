// Corresponds to the ConfluenceUpload model in the Django backend
// and the ConfluenceUploadSerializer

export interface ConfluenceUpload {
  id: number;
  file_url?: string; // URL to download the originally uploaded file, if available/needed
  user?: number; // User ID
  user_username?: string;
  uploaded_at: string; // ISO date string

  status: string; // Old overall status e.g. 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'

  // New detailed progress fields
  progress_status: string; // e.g. 'PENDING', 'EXTRACTING', 'PARSING_METADATA', etc.
  progress_status_display: string; // Human-readable version of progress_status
  progress_percent: number; // 0-100

  task_id?: string | null;

  target_workspace?: number | null; // Workspace ID
  target_workspace_id?: number | null;
  target_workspace_name?: string | null;

  target_space?: number | null; // Space ID
  target_space_id?: number | null;
  target_space_name?: string | null;

  pages_succeeded_count: number;
  pages_failed_count: number;
  attachments_succeeded_count: number;

  progress_message?: string | null;
  error_details?: string | null;
}
