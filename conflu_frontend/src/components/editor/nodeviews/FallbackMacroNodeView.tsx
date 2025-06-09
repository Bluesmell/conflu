import React, { useState, useEffect } from 'react'; // Added useEffect
import { NodeViewWrapper, NodeViewProps } from '@tiptap/react';
import { getFallbackMacroDetails } from '../../../services/api';
import { FallbackMacro } from '../../../types/apiModels'; // Ensure FallbackMacro type is defined
import styles from './FallbackMacroNodeView.module.css';

const FallbackMacroNodeView: React.FC<NodeViewProps> = ({ node, editor, getPos }) => {
  const { macroName, fallbackMacroId } = node.attrs;
  const [details, setDetails] = useState<FallbackMacro | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);

  const fetchDetails = async () => {
    if (!fallbackMacroId) {
      setError('No Fallback ID available.');
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await getFallbackMacroDetails(fallbackMacroId);
      setDetails(data);
    } catch (err) {
      setError('Failed to fetch details.');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleDetails = (event: React.MouseEvent) => {
    event.preventDefault(); // Prevent editor focus issues or other default behaviors
    const newShowDetails = !showDetails;
    setShowDetails(newShowDetails);
    if (newShowDetails && !details && fallbackMacroId) {
      fetchDetails();
    }
  };

  // Optional: Allow selecting the node when clicking on it, if not default
  const handleNodeClick = () => {
    if (typeof getPos === 'function' && editor && !editor.isFocused) {
       // Select the node when its wrapper is clicked, if editor is not focused
       // This helps in making sure Tiptap's selection is updated.
       editor.commands.setNodeSelection(getPos());
    }
  };


  return (
    <NodeViewWrapper
        className={`${styles.fallbackMacroWrapper} ${editor.isEditable ? styles.editable : ''}`}
        onClick={handleNodeClick}
        draggable="true" // Ensure draggable is true on the wrapper
        data-drag-handle // Optional: if you want the whole node to be a drag handle
    >
      <div className={styles.header} contentEditable={false}> {/* contentEditable false for UI elements */}
        <strong>Unsupported Macro: {macroName}</strong>
        {fallbackMacroId != null && ( // Check for null or undefined explicitly
          <button onClick={handleToggleDetails} className={styles.toggleButton}>
            {showDetails ? 'Hide' : 'Show'} Details (ID: {fallbackMacroId})
          </button>
        )}
      </div>
      {showDetails && fallbackMacroId != null && (
        <div className={styles.details} contentEditable={false}>
          {isLoading && <p>Loading details...</p>}
          {error && <p className={styles.error}>{error}</p>}
          {details && (
            <pre className={styles.rawContent}>{details.raw_macro_content}</pre>
          )}
          {!details && !isLoading && !error && <p>No details loaded yet.</p>}
        </div>
      )}
    </NodeViewWrapper>
  );
};

export default FallbackMacroNodeView;
