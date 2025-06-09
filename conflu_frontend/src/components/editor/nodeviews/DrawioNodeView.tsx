import React, { useState, useEffect } from 'react';
import { NodeViewWrapper, NodeViewProps }_from '@tiptap/react';
import styles from './DrawioNodeView.module.css'; // To be created

// Placeholder for actual SVG rendering or image preview logic
const renderDiagramPreview = (xml: string | null): string => {
  if (!xml || xml.trim() === '') {
    return '<p>Empty Draw.io Diagram</p>';
  }
  // In a real scenario, you'd convert XML to SVG/PNG here or use an <img> tag
  // For now, just indicate that there's content.
  // Extracting name or a simple preview from Draw.io XML is non-trivial without a library.
  return `<div style="border:1px solid #ccc; padding:10px; text-align:center;">
            <p>Draw.io Diagram</p>
            <p><small>(Preview not available in this view)</small></p>
            <pre style="font-size:0.7em; max-height:50px; overflow:hidden; text-align:left; white-space:pre-wrap;">${xml.substring(0,100)}...</pre>
          </div>`;
};


const DrawioNodeView: React.FC<NodeViewProps> = ({ node, editor, updateAttributes, getPos }) => {
  const [xmlContent, setXmlContent] = useState<string>(node.attrs.xml || '');
  const [isPreviewLoading, setIsPreviewLoading] = useState(false); // For future async preview rendering

  // The modal state and open/close handlers live in EditorView.tsx (or a context).
  // This NodeView will dispatch an event to request the modal to open.
  const handleOpenDrawioModal = () => {
    if (editor.isEditable) {
      // Dispatch a custom event that EditorView will listen for.
      // Pass current XML and a callback to update this node's attributes.
      const event = new CustomEvent('open-drawio-editor', {
        detail: {
          initialXml: node.attrs.xml,
          onSaveCallback: (newXml: string) => {
            updateAttributes({ xml: newXml });
            // Optionally, force a re-render or update local state if preview depends on it
            // setXmlContent(newXml); // If local state 'xmlContent' is used for preview
          },
          // pos: getPos(), // Optionally pass position if EditorView needs it for some reason
        }
      });
      window.dispatchEvent(event);
    }
  };

  // When node.attrs.xml changes (e.g., by undo/redo or external update),
  // update local state if you are using one for rendering the preview.
  // For this basic placeholder, we directly use node.attrs.xml in render logic.
  // If `xmlContent` state was used for `renderDiagramPreview`, this useEffect would be:
  useEffect(() => {
     if (node.attrs.xml !== xmlContent) { // Assuming xmlContent state exists
       setXmlContent(node.attrs.xml);
     }
  }, [node.attrs.xml, xmlContent]); // xmlContent dependency if it's a state

  // Use node.attrs.xml directly for the preview to always reflect Tiptap's state
  const currentPreviewHtml = renderDiagramPreview(node.attrs.xml);

  return (
    <NodeViewWrapper className={styles.drawioNodeWrapper} data-drag-handle>
      <div className={styles.contentArea} contentEditable={false}>
        {isPreviewLoading ? (
          <p>Loading preview...</p>
        ) : (
          <div dangerouslySetInnerHTML={{ __html: currentPreviewHtml }} />
        )}
      </div>
      {editor.isEditable && (
        <button
          className={styles.editButton}
          onClick={handleOpenDrawioModal}
          title="Edit Draw.io Diagram"
          contentEditable={false}
        >
          Edit Diagram
        </button>
      )}
    </NodeViewWrapper>
  );
};

export default DrawioNodeView;
