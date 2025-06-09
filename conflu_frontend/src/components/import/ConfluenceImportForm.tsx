import React, { useState, useEffect, FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { initiateConfluenceImport, fetchSpaces } from '../../services/api'; // Using fetchSpaces for workspaces
import { Space } from '../../types/apiModels'; // Assuming Space can represent Workspace for selection
import styles from './ConfluenceImportForm.module.css'; // To be created

const ConfluenceImportForm: React.FC = () => {
  const [file, setFile] = useState<File | null>(null);
  const [targetWorkspaceId, setTargetWorkspaceId] = useState<string>('');
  // const [targetSpaceId, setTargetSpaceId] = useState<string>(''); // For now, only workspace selection
  const [workspaces, setWorkspaces] = useState<Space[]>([]); // Using Space type for workspaces
  const [isLoading, setIsLoading] = useState(false);
  const [isFetchingWorkspaces, setIsFetchingWorkspaces] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const loadWorkspaces = async () => {
      setIsFetchingWorkspaces(true);
      try {
        // Assuming fetchSpaces() returns a list of items that can serve as "workspaces"
        // The backend `ConfluenceUpload` model has `target_workspace` and `target_space`.
        // For simplicity, if your `Space` model in frontend/backend represents a top-level container,
        // we can use it for `target_workspace_id`.
        // If your backend `Space` is a child of `Workspace`, then `fetchSpaces` might list actual spaces,
        // and you might need a separate `fetchWorkspaces` endpoint.
        // For this form, we'll assume `fetchSpaces` lists selectable parent entities (workspaces).
        const fetchedWorkspaces = await fetchSpaces();
        setWorkspaces(fetchedWorkspaces);
      } catch (err) {
        console.error("Failed to fetch workspaces:", err);
        // Don't block form usage if workspace fetching fails, user can still upload without target
      } finally {
        setIsFetchingWorkspaces(false);
      }
    };
    loadWorkspaces();
  }, []);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files[0]) {
      setFile(event.target.files[0]);
      setError(null); // Clear previous file errors
    } else {
      setFile(null);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError('Please select a ZIP file to upload.');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Pass workspaceId if selected. targetSpaceId is not implemented in this simplified form.
      const response = await initiateConfluenceImport(file, targetWorkspaceId ? parseInt(targetWorkspaceId) : undefined);

      // Assuming response contains the ID of the ConfluenceUpload record, e.g., response.id
      // The actual field name in response might be `id`, `pk`, `upload_id`, or `task_id`.
      // Check your backend's ConfluenceUploadSerializer.
      const uploadId = response.id; // Adjust if needed based on actual API response structure

      if (uploadId) {
        navigate(`/import/status/${uploadId}`);
      } else {
        setError("Import initiated, but did not receive an Upload ID. Please check system status.");
        console.error("API Response for initiateConfluenceImport:", response);
      }
    } catch (err: any) {
      console.error('Import initiation failed:', err);
      setError(err.response?.data?.error || err.message || 'Failed to initiate import. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className={styles.importForm}>
      {error && <p className={styles.errorMessage}>{error}</p>}

      <div className={styles.formGroup}>
        <label htmlFor="file-upload">Confluence ZIP File:</label>
        <input
          type="file"
          id="file-upload"
          accept=".zip"
          onChange={handleFileChange}
          required
          disabled={isLoading}
        />
      </div>

      <div className={styles.formGroup}>
        <label htmlFor="workspace-select">Target Workspace (Optional):</label>
        <select
          id="workspace-select"
          value={targetWorkspaceId}
          onChange={(e) => setTargetWorkspaceId(e.target.value)}
          disabled={isLoading || isFetchingWorkspaces}
        >
          <option value="">{isFetchingWorkspaces ? "Loading workspaces..." : "Select a workspace (optional)"}</option>
          {workspaces.map((ws) => (
            // Assuming 'Space' items from fetchSpaces have 'id' and 'name'
            // and can represent a "Workspace" for import targeting.
            <option key={ws.id} value={ws.id}>
              {ws.name} (ID: {ws.id}, Key: {ws.key})
            </option>
          ))}
        </select>
        <p className={styles.fieldDescription}>
          If no workspace is selected, the system may use a default or the import might be restricted.
        </p>
      </div>

      {/* Placeholder for Target Space selection if needed in future */}
      {/* <div className={styles.formGroup}>
        <label htmlFor="space-select">Target Space (Optional, within selected Workspace):</label>
        <input type="text" id="space-select" placeholder="Enter Space Key/ID (if applicable)" />
      </div> */}

      <button type="submit" disabled={isLoading || !file} className={styles.submitButton}>
        {isLoading ? 'Uploading and Initiating...' : 'Start Import'}
      </button>
    </form>
  );
};

export default ConfluenceImportForm;
