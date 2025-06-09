import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { getConfluenceImportStatus } from '../services/api'; // Assuming api.ts is updated
import { ConfluenceUpload } from '../types/importerModels'; // Assuming this type is defined

const ImportStatusPage: React.FC = () => {
  const { uploadId } = useParams<{ uploadId: string }>();
  const navigate = useNavigate();
  const [importDetails, setImportDetails] = useState<ConfluenceUpload | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pollingIntervalId, setPollingIntervalId] = useState<NodeJS.Timeout | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!uploadId) {
      setError("Upload ID is missing.");
      setIsLoading(false);
      return;
    }
    try {
      // setIsLoading(true); // Optionally set loading for each poll, or just initially
      const data = await getConfluenceImportStatus(uploadId);
      setImportDetails(data);
      setError(null);

      // Stop polling if completed or failed
      if (data.progress_status === 'COMPLETED' || data.progress_status === 'FAILED') {
        if (pollingIntervalId) clearInterval(pollingIntervalId);
        setPollingIntervalId(null);
      }
    } catch (err: any) {
      console.error("Failed to fetch import status:", err);
      setError(err.message || "Failed to fetch import status. Please try refreshing.");
      // Potentially stop polling on certain types of errors
      if (pollingIntervalId) clearInterval(pollingIntervalId);
      setPollingIntervalId(null);
    } finally {
      setIsLoading(false); // Set to false after first load
    }
  }, [uploadId, pollingIntervalId]);

  useEffect(() => {
    fetchStatus(); // Initial fetch

    const intervalId = setInterval(() => {
      fetchStatus();
    }, 5000); // Poll every 5 seconds

    setPollingIntervalId(intervalId);

    return () => { // Cleanup on component unmount
      if (intervalId) clearInterval(intervalId);
    };
  }, [fetchStatus]); // Rerun effect if fetchStatus changes (due to uploadId)

  if (isLoading && !importDetails) {
    return <p>Loading import status...</p>;
  }

  if (error && !importDetails) { // Show critical error if no details ever loaded
    return <p style={{ color: 'red' }}>Error: {error}</p>;
  }

  if (!importDetails) {
    return <p>No import details available. This might be an invalid Upload ID or the record is not found.</p>;
  }

  const isTerminalState = importDetails.progress_status === 'COMPLETED' || importDetails.progress_status === 'FAILED';

  return (
    <div style={{ padding: '20px' }}>
      <h1>Confluence Import Status</h1>
      <p><strong>Upload ID:</strong> {importDetails.id}</p>
      <p><strong>Uploaded At:</strong> {new Date(importDetails.uploaded_at).toLocaleString()}</p>
      <p><strong>Overall Status:</strong> {importDetails.status}</p>

      <h2>Progress Details</h2>
      <p><strong>Current Step:</strong> {importDetails.progress_status_display || importDetails.progress_status}</p>
      <p><strong>Progress:</strong> {importDetails.progress_percent}%</p>
      {importDetails.progress_message && <p><strong>Message:</strong> {importDetails.progress_message}</p>}

      <div style={{ width: '100%', backgroundColor: '#eee', borderRadius: '4px', margin: '10px 0' }}>
        <div
          style={{
            width: `${importDetails.progress_percent}%`,
            backgroundColor: isTerminalState && importDetails.progress_status === 'FAILED' ? 'red' : 'green',
            height: '20px',
            borderRadius: '4px',
            textAlign: 'center',
            color: 'white',
            lineHeight: '20px',
            transition: 'width 0.3s ease-in-out'
          }}
        >
          {importDetails.progress_percent}%
        </div>
      </div>

      <h3>Summary</h3>
      <p>Pages Succeeded: {importDetails.pages_succeeded_count}</p>
      <p>Pages Failed/Skipped: {importDetails.pages_failed_count}</p>
      <p>Attachments Processed: {importDetails.attachments_succeeded_count}</p>

      {importDetails.error_details && (
        <>
          <h3>Error Details:</h3>
          <pre style={{ whiteSpace: 'pre-wrap', backgroundColor: '#f8d7da', color: '#721c24', padding: '10px', borderRadius: '4px' }}>
            {importDetails.error_details}
          </pre>
        </>
      )}

      {isTerminalState && importDetails.progress_status === 'COMPLETED' && importDetails.target_space_id && (
        <p>
          Import completed successfully!
          <Link to={`/spaces/${importDetails.target_space_name || importDetails.target_space_id}`}> {/* Adjust link as per actual space key/ID for URL */}
            Go to imported space: {importDetails.target_space_name || `Space ID ${importDetails.target_space_id}`}
          </Link>
        </p>
      )}
      {isTerminalState && importDetails.progress_status === 'FAILED' && (
        <p style={{color: 'red'}}>Import failed. Please check the error details above.</p>
      )}

      {!isTerminalState && <p>This page will automatically refresh with the latest status.</p>}

      <button onClick={() => navigate('/')} style={{marginTop: '20px'}}>Go to Dashboard</button>
      {/* We might need a page to list all imports, or link from where import was initiated */}
    </div>
  );
};

export default ImportStatusPage;
