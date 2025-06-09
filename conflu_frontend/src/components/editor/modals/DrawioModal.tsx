import React from 'react';
import styles from './DrawioModal.module.css'; // To be created

interface DrawioModalProps {
  isOpen: boolean;
  onClose: () => void;
  initialXml: string | null; // XML content to load into Draw.io
  onSave: (newXml: string) => void; // Callback when Draw.io saves
}

const DrawioModal: React.FC<DrawioModalProps> = ({
  isOpen,
  onClose,
  initialXml,
  onSave,
}) => {
  const iframeRef = React.useRef<HTMLIFrameElement>(null);
  const [iframeLoaded, setIframeLoaded] = React.useState(false);

  const drawioUrl = 'https://embed.diagrams.net/?embed=1&ui=atlas&spin=1&proto=json&configure=1';
  // For self-hosted: const drawioUrl = 'YOUR_SELF_HOSTED_DRAWIO_URL';

  // Handle messages from Draw.io iframe
  React.useEffect(() => {
    if (!isOpen) return;

    const handleMessage = (event: MessageEvent) => {
      if (!event.data || typeof event.data !== 'string' || event.source !== iframeRef.current?.contentWindow) {
        return;
      }

      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch (e) {
        console.error('Failed to parse message from Draw.io:', e);
        return;
      }

      console.log('Message from Draw.io:', msg);

      switch (msg.event) {
        case 'init':
          setIframeLoaded(true);
          // Iframe is ready, load the initial XML
          if (iframeRef.current?.contentWindow) {
            iframeRef.current.contentWindow.postMessage(
              JSON.stringify({
                action: 'load',
                xml: initialXml || '', // Send empty string for new diagrams
                // autosave: 1, // Optional: enable autosave in Draw.io
              }),
              '*' // Or specify targetOrigin for security if known
            );
          }
          break;
        case 'load':
          // Diagram loaded in iframe
          console.log('Draw.io: Diagram loaded.');
          break;
        case 'save':
          // User clicked save in Draw.io editor
          onSave(msg.xml); // Pass XML data to parent
          // Optional: Trigger export then close, or let Draw.io handle its own save flow
          // if (msg.exit) { onClose(); } // Close if exit is also part of save
          break;
        case 'autosave':
           // Autosave event, msg.xml contains the data
           onSave(msg.xml); // Update parent with autosaved XML
           break;
        case 'export':
          // This event gives the exported data (e.g. SVG, PNG) if export action was triggered
          // For now, we primarily care about saving the XML.
          console.log('Draw.io: Diagram exported. Data:', msg.data);
          // If we trigger an export for preview, this is where we'd get it.
          // After export, close the modal.
          onSave(msg.xml || initialXml || ''); // Ensure XML is saved before closing on export
          onClose();
          break;
        case 'exit':
          // User closed Draw.io editor (e.g., clicked cancel or saved and exited)
          // The 'save' event should handle data persistence.
          // 'exit' might have unsaved data if user cancels.
          // The `onSave` prop should have been called if user saved.
          // If msg.modified is true, prompt user? For now, just close.
          onClose();
          break;
        default:
          // console.log('Unhandled Draw.io event:', msg.event);
          break;
      }
    };

    window.addEventListener('message', handleMessage);
    return () => {
      window.removeEventListener('message', handleMessage);
      setIframeLoaded(false); // Reset loaded state when modal closes or reopens
    };
  }, [isOpen, initialXml, onSave, onClose]);

  // Configure Draw.io on load
  useEffect(() => {
      if (isOpen && iframeLoaded && iframeRef.current?.contentWindow) {
          iframeRef.current.contentWindow.postMessage(JSON.stringify({
              action: 'configure',
              config: {
                  // Example: customize editor
                  // "css": "body { background-color: #f0f0f0; }",
                  "defaultFonts": ["Humor Sans", "Helvetica", "Times New Roman"],
                  // Full list of configurable options: https://www.drawio.com/doc/faq/configure-diagram-editor
              }
          }), '*');
      }
  }, [isOpen, iframeLoaded]);


  if (!isOpen) {
    return null;
  }

  return (
    <div className={styles.modalOverlay}>
      <div className={styles.modalContent}>
        <div className={styles.modalHeader}>
          <h2>Draw.io Diagram Editor</h2>
          <button
            onClick={() => { // Simulate 'exit' or 'save then exit'
                if (iframeRef.current?.contentWindow) {
                    // To get the latest XML before closing, trigger an export action.
                    // The 'export' event will then call onSave and onClose.
                    // Choose 'xmlsvg' for SVG preview if needed, or just 'xml' for data.
                    iframeRef.current.contentWindow.postMessage(JSON.stringify({
                        action: 'export',
                        format: 'xml', // We just need the XML
                        // exit: true // Some versions might support this in export
                    }), '*');
                    // As a fallback if export doesn't trigger exit:
                    // setTimeout(onClose, 500); // Give time for export message
                } else {
                    onClose(); // Fallback if iframe not ready
                }
            }}
            className={styles.closeButton}
            title="Save & Close"
          >
            &#10003; {/* Checkmark for Save & Close */}
          </button>
        </div>
        <div className={styles.modalBody}>
          <iframe
            ref={iframeRef}
            src={drawioUrl}
            title="Draw.io Editor"
            sandbox="allow-forms allow-scripts allow-same-origin allow-popups allow-downloads allow-modals"
            // Added allow-modals for Draw.io's own dialogs
          />
        </div>
      </div>
    </div>
  );
};

export default DrawioModal;
