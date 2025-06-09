import React, { useEffect, useState, useCallback, useRef } from 'react';
import { NodeViewWrapper, NodeViewProps }_from '@tiptap/react';
import mermaid from 'mermaid';
import { useDebounce } from '../../../hooks/useDebounce'; // A custom debounce hook (to be created or use lodash)
import styles from './MermaidNodeView.module.css';
import { validateMermaidSyntax } from '../../../services/api'; // Import validation function

mermaid.initialize({
  startOnLoad: false, // We will render manually
  // theme: 'default', // or 'dark', 'forest', 'neutral'
  // securityLevel: 'strict', // or 'loose', 'antiscript'
});

const MermaidNodeView: React.FC<NodeViewProps> = ({ node, updateAttributes, editor }) => {
  const initialSyntax = node.attrs.syntax || 'graph TD\nA-->B';
  const [syntax, setSyntax] = useState<string>(initialSyntax);
  const [renderedDiagram, setRenderedDiagram] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const diagramRef = useRef<HTMLDivElement>(null);

  const debouncedSyntax = useDebounce(syntax, 750); // Debounce for 750ms

  const renderMermaid = useCallback(async (currentSyntax: string) => {
    if (!diagramRef.current) return;

    try {
      // Check if syntax is empty or just whitespace
      if (!currentSyntax.trim()) {
        setRenderedDiagram('');
        setErrorMessage(null);
        diagramRef.current.innerHTML = ''; // Clear previous diagram
        return;
      }

      // Basic client-side validation (Mermaid's parse a_nd render will also validate)
      await mermaid.parse(currentSyntax); // Throws error on invalid syntax
      const { svg } = await mermaid.render(`mermaid-diagram-${node.ID}`, currentSyntax);
      setRenderedDiagram(svg);
      setErrorMessage(null);
    } catch (error: any) {
      console.warn("Mermaid rendering error:", error.message || error);
      setRenderedDiagram(''); // Clear diagram on error
      setErrorMessage(error.message || 'Invalid Mermaid syntax');
    }
  }, [node.ID]);

  useEffect(() => {
    renderMermaid(debouncedSyntax);
  }, [debouncedSyntax, renderMermaid]);

  // Update Tiptap node attribute when local syntax changes (debounced)
  useEffect(() => {
    // Only update if the debounced syntax is different from what's in the node attributes
    // to prevent unnecessary updates or loops if debouncedSyntax is initially same as node.attrs.syntax
    if (debouncedSyntax !== node.attrs.syntax) {
      updateAttributes({ syntax: debouncedSyntax });
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSyntax, updateAttributes]); // Don't add node.attrs.syntax here to avoid loops

  const handleSyntaxChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setSyntax(event.target.value);
  };

  // When the node is initially created or its syntax attribute changes from outside
  useEffect(() => {
    if (node.attrs.syntax !== syntax) {
      setSyntax(node.attrs.syntax);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.attrs.syntax]);


  // For backend validation (to be implemented fully later)
  const [isValidating, setIsValidating] = useState(false);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const handleValidateSyntax = async () => {
    setIsValidating(true);
    setValidationMessage(null);
    try {
      const response = await validateMermaidSyntax(syntax);
      if (response.is_valid) {
        setValidationMessage("Syntax is valid!");
        // Optionally clear diagram error if previously invalid from rendering
        if (errorMessage) setErrorMessage(null);
        // Re-render with potentially corrected syntax if validation implies it fixed something
        // or if validation is separate from rendering's own error handling.
        // renderMermaid(syntax); // Usually not needed if renderMermaid already runs on syntax change.
      } else {
        setValidationMessage(`Invalid: ${response.error_message || 'Unknown validation error.'}`);
      }
    } catch (err: any) {
      console.error("Validation API call failed:", err);
      setValidationMessage(`Validation request failed: ${err.message || 'Network error'}`);
    } finally {
      setIsValidating(false);
    }
    // alert("Backend validation not yet fully implemented for this button.");
    // setIsValidating(false);
  };


  return (
    <NodeViewWrapper className={styles.mermaidNodeWrapper}>
      <div className={styles.controls} contentEditable={false}>
        <label htmlFor={`mermaid-syntax-${node.ID}`}>Mermaid Syntax:</label>
        <button onClick={handleValidateSyntax} disabled={isValidating || !syntax.trim()} style={{ marginLeft: '10px' }}>
          {isValidating ? 'Validating...' : 'Validate Syntax'}
        </button>
      </div>
      <textarea
        id={`mermaid-syntax-${node.ID}`}
        value={syntax}
        onChange={handleSyntaxChange}
        className={`${styles.syntaxInput} ${errorMessage ? styles.syntaxError : ''}`}
        rows={Math.max(3, syntax.split('\n').length)} // Auto-adjust rows
        spellCheck="false"
        disabled={!editor.isEditable}
      />
      {validationMessage &&
        <div className={`${styles.validationMessage} ${validationMessage.startsWith("Invalid:") ? styles.invalid : styles.valid}`}>
          {validationMessage}
        </div>
      }

      <div className={styles.previewHeader} contentEditable={false}>Preview:</div>
      {errorMessage && <div className={styles.errorMessagePreview}>{errorMessage}</div>}
      <div
        ref={diagramRef}
        className={styles.diagramPreview}
        dangerouslySetInnerHTML={{ __html: renderedDiagram }}
      />
    </NodeViewWrapper>
  );
};

export default MermaidNodeView;
