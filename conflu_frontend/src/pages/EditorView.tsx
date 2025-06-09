import React, { useEffect, useState, useCallback, useRef } from 'react'; // Added useRef
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import TiptapEditor from '../components/editor/TiptapEditor';
import { fetchPageDetails, createPage, updatePage } from '../services/api';
import { Page } from '../types/apiModels';
// import { appSchema } from '../editor/schema'; // If needed for Markdown conversion utilities
// import { Markdown } from '@tiptap/extension-markdown'; // Placeholder if it can be installed
import DrawioModal from '../components/editor/modals/DrawioModal'; // Import DrawioModal

// Helper to get initial content (empty ProseMirror doc)
const getEmptyDocJson = () => JSON.stringify({
  type: 'doc',
  content: [{ type: 'paragraph' }],
});
const getEmptyDocHtml = () => '<p></p>';


const EditorView: React.FC = () => {
  const { spaceKey, pageId } = useParams<{ spaceKey: string; pageId?: string }>(); // pageId is optional for new pages
  const navigate = useNavigate();
  const location = useLocation();

  const [pageTitle, setPageTitle] = useState('');
  const [editorContentJson, setEditorContentJson] = useState<string>(getEmptyDocJson());
  // const [editorContentHtml, setEditorContentHtml] = useState<string>(getEmptyDocHtml()); // HTML content less critical for this view's state
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parentPageId, setParentPageId] = useState<string | null>(null);

  // State for Markdown mode
  const [isMarkdownMode, setIsMarkdownMode] = useState(false);
  const [markdownContent, setMarkdownContent] = useState<string>('');
  const markdownContentRef = useRef<string>('');

  // State for Draw.io Modal
  const [isDrawioModalOpen, setIsDrawioModalOpen] = useState(false);
  // currentDrawioXml and drawioNodePos are part of currentEditingDrawioNode
  // const [currentDrawioXml, setCurrentDrawioXml] = useState<string | null>(null);
  // const [drawioNodePos, setDrawioNodePos] = useState<number | null>(null);

  interface EditingDrawioNode {
    initialXml: string;
    onSaveCallback: (newXml: string) => void; // This callback will execute node's updateAttributes
  }
  const [currentEditingDrawioNode, setCurrentEditingDrawioNode] = useState<EditingDrawioNode | null>(null);

  // Ref to access Tiptap editor instance. This should be passed to TiptapEditor component.
  // This is a simplified way; TiptapEditor might need to expose its editor instance via a ref or callback.
  // For now, we'll assume direct editor interaction for Draw.io save is handled conceptually
  // by passing a save function to the NodeView, which then calls updateAttributes.
  // The EditorView itself doesn't need the `editor` instance directly if NodeViews handle their own updates.
  // However, the NodeView *will* need a way to tell EditorView to open the modal.
  // We can use a callback prop for that on TiptapEditor, or a global event/context.

  // Let's simulate a global event bus or context for opening the modal for now.
  // This is a common pattern for decoupling NodeViews from page-level state.
  // In a real app, Zustand, Redux, or React Context would be better.
  useEffect(() => {
    const handleOpenDrawioEditorEvent = (event: Event) => {
      const customEvent = event as CustomEvent;
      const { initialXml, onSaveCallback } = customEvent.detail;
      setCurrentEditingDrawioNode({ initialXml, onSaveCallback });
      setIsDrawioModalOpen(true);
    };
    window.addEventListener('open-drawio-editor', handleOpenDrawioEditorEvent);
    return () => window.removeEventListener('open-drawio-editor', handleOpenDrawioEditorEvent);
  }, []);

  const handleDrawioModalSave = (newXml: string) => {
    if (currentEditingDrawioNode) {
      currentEditingDrawioNode.onSaveCallback(newXml); // This calls DrawioNodeView's updateAttributes
    }
    setIsDrawioModalOpen(false);
    setCurrentEditingDrawioNode(null);
  };

  const handleDrawioModalClose = () => {
    setIsDrawioModalOpen(false);
    setCurrentEditingDrawioNode(null);
  };

  // For now, we'll manage content through props/callbacks and simulate markdown conversion.
  // A more direct editor ref would be: const tiptapEditorRef = useRef<Editor | null>(null);

  useEffect(() => {
    const queryParams = new URLSearchParams(location.search);
    setParentPageId(queryParams.get('parent'));
  }, [location.search]);

  useEffect(() => {
    if (pageId) { // If pageId exists, we are editing an existing page
      setIsLoading(true);
      setError(null);
      fetchPageDetails(pageId)
        .then((data: Page) => {
          setPageTitle(data.title);
          // Ensure raw_content is a string, TiptapEditor will parse if it's JSON string
          let initialJson = getEmptyDocJson();
          if (typeof data.raw_content === 'object') {
            initialJson = JSON.stringify(data.raw_content);
          } else if (typeof data.raw_content === 'string') {
            // Attempt to parse if it's a JSON string, otherwise it's an issue or needs HTML->JSON conversion
            try {
              JSON.parse(data.raw_content); // Validate
              initialJson = data.raw_content;
            } catch (e) {
              console.warn("raw_content is a string but not valid JSON. Treating as error or needing conversion.", e);
              setError("Loaded page content is in an unexpected string format.");
              // Potentially try to parse data.raw_content as HTML into ProseMirror JSON here if that's a case
            }
          }
          setEditorContentJson(initialJson);
          // If starting in markdown mode or for later use, convert initialJson to markdown
          // This requires editor instance or a utility. For now, set raw markdown empty.
          // setMarkdownContent(convertToMarkdown(initialJson)); // Placeholder
        })
        .catch(err => {
          console.error('Failed to load page:', err);
          setError('Failed to load page content. You might be creating a new page if this is not an edit view.');
          setEditorContentJson(getEmptyDocJson());
        })
        .finally(() => setIsLoading(false));
    } else { // New page
      setPageTitle('');
      setEditorContentJson(getEmptyDocJson());
      // setMarkdownContent(''); // Empty for new page
      setIsLoading(false);
    }
  }, [pageId]);

  const handleEditorChange = useCallback((newContentJson: string, _newContentHtml: string) => {
    setEditorContentJson(newContentJson);
    // If not in markdown mode, update markdown state too for seamless switch
    if (!isMarkdownMode) {
      // This is where editor.storage.markdown.getMarkdown() would be ideal.
      // Simulating: In a real scenario, TiptapEditor would expose its editor instance
      // or a method to get markdown.
      // For now, this won't update markdownContent in real-time from WYSIWYG.
      // setMarkdownContent(convertToMarkdown(newContentJson)); // Placeholder
    }
  }, [isMarkdownMode]);

  const handleMarkdownChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMarkdownContent(event.target.value);
    markdownContentRef.current = event.target.value;
  };

  const toggleEditorMode = () => {
    if (isMarkdownMode) { // Switching from Markdown to Rich Text
      // The TiptapEditor needs to re-initialize with markdownContent.
      // This can be done by changing its `key` prop to force re-mount,
      // or by having TiptapEditor internally use `editor.commands.setContent(newMarkdownContent, true)`.
      // For simplicity, we'll update editorContentJson which TiptapEditor consumes.
      // This implies TiptapEditor needs to be enhanced to parse markdown if its `content` prop changes this way.
      // OR, TiptapEditor's `onChange` should have been Markdown-aware.
      // For now, assume setEditorContentJson will trigger TiptapEditor to parse (if it were HTML/JSON string).
      // To make Tiptap parse markdown, `setContent` needs to be called.
      // This is a conceptual gap without direct editor access here.
      // Simplification: assume TiptapEditor's `content` prop can take markdown string
      // if a special flag is passed or if the Markdown extension auto-parses string content.
      // This is NOT standard Tiptap behavior for the `content` prop directly.
      // A real implementation needs editor.commands.setContent(markdownContentRef.current, true);

      // Simulate conversion for now: treat markdown as if it's the new source of truth for JSON
      // This is a placeholder. Real conversion from MD to JSON is needed.
      console.warn("Switching to Rich Text: Content will be set from Markdown. Actual MD->JSON parsing needs editor instance.");
      // setEditorContentJson(markdownContentRef.current); // This would make Tiptap try to parse MD as JSON/HTML.
                                                        // This part is tricky without direct editor.commands.setContent
                                                        // or a utility.
      // Let's assume for now that saving while in markdown mode will handle the conversion.
      // When switching back to RichText, we ideally want the TiptapEditor to parse markdownContentRef.current.
      // This might require passing markdownContent to TiptapEditor and having it handle it.
      // For now, if we switch back, the TiptapEditor will still have its last JSON state.
      // The user would need to save from Markdown mode to make MD changes stick to JSON.

    } else { // Switching from Rich Text to Markdown
      // This is where editor.storage.markdown.getMarkdown() would be used.
      // Placeholder:
      console.warn("Switching to Markdown: Markdown content should be generated from current Tiptap JSON. Placeholder used.");
      // setMarkdownContent("### Markdown from Tiptap JSON (placeholder)\n" + editorContentJson);
      // markdownContentRef.current = "### Markdown from Tiptap JSON (placeholder)\n" + editorContentJson;
      // If editorContentJson is up-to-date, we can try a rough JSON to text for now for textarea
      try {
        const parsed = JSON.parse(editorContentJson);
        const plainText = prosemirrorJsonToTextForView(parsed); // Basic text extraction
        setMarkdownContent(plainText); // Very basic representation
        markdownContentRef.current = plainText;
      } catch {
        setMarkdownContent("# Could not parse JSON to generate basic Markdown preview.");
        markdownContentRef.current = "# Could not parse JSON to generate basic Markdown preview.";
      }
    }
    setIsMarkdownMode(!isMarkdownMode);
  };

  // Basic text extractor from ProseMirror JSON (similar to backend's)
  // This is NOT a real Markdown converter.
  const prosemirrorJsonToTextForView = (json_content: any): string => {
    if (!json_content || typeof json_content !== 'object' || !json_content.content) return '';
    let text = '';
    function recurse(node: any) {
      if (node.type === 'text' && node.text) text += node.text;
      if (node.content) node.content.forEach(recurse);
      if (node.type === 'paragraph' || node.type === 'heading') text += '\n'; // Basic newlines
    }
    json_content.content.forEach(recurse);
    return text.trim();
  };


  const handleSave = async () => {
    if (!spaceKey && !pageId) {
      setError("Cannot save page: Space context is missing.");
      return;
    }
    if (!pageTitle.trim()) {
        setError("Cannot save page: Title is required.");
        return;
    }

    setIsSaving(true);
    setError(null);

    try {
      let savedPage: Page;
      let finalJsonToSave;

      if (isMarkdownMode) {
        // Here, ideally, we'd use a robust Markdown to ProseMirror JSON conversion.
        // For now, we'll use a placeholder or log a warning.
        // This part is CRITICAL if the Markdown extension isn't working in TiptapEditor.
        // If TiptapEditor *had* a ref: editorRef.current?.commands.setContent(markdownContentRef.current, true);
        // finalJsonToSave = editorRef.current?.getJSON();
        console.warn("Saving from Markdown mode: Conversion from Markdown to JSON is currently conceptual/placeholder.");
        // As a temporary measure, if we can't convert MD, we might save the last known JSON.
        // This means MD edits might not be saved if MD extension isn't working.
        // For the purpose of this task, we'll assume this conversion step is tricky
        // without the actual extension functioning to parse markdownContentRef.current.
        // Fallback to editorContentJson which holds the JSON from the last rich text edit.
        // This is NOT ideal. A real solution requires MD parsing.
        try {
            // Simulate that editorContentJson is updated from markdownContentRef.current
            // This is where editor.commands.setContent(markdownContentRef.current, true) would happen.
            // Since we don't have direct editor access here, we'll assume editorContentJson might be stale if in MD mode.
            // The save button should ideally trigger the conversion if in markdown mode.
            // For this exercise, let's assume if isMarkdownMode, the markdownContent is the source of truth
            // and we'd need a utility to convert it.
            // If no such utility:
            alert("Saving from Markdown mode is not fully implemented without a Markdown parser. Saving last rich text JSON.");
            finalJsonToSave = JSON.parse(editorContentJson);

        } catch (e) {
            setError("Error parsing current content for saving.");
            setIsSaving(false);
            return;
        }

      } else {
        try {
            finalJsonToSave = JSON.parse(editorContentJson);
        } catch (e) {
            setError("Error parsing rich text content for saving.");
            setIsSaving(false);
            return;
        }
      }

      if (!finalJsonToSave) {
        setError("Content is empty or invalid.");
        setIsSaving(false);
        return;
      }

      if (pageId) { // Existing page
        savedPage = await updatePage(pageId, pageTitle, finalJsonToSave);
      } else if (spaceKey) { // New page
        savedPage = await createPage(spaceKey, pageTitle, finalJsonToSave, parentPageId || undefined);
      } else {
        throw new Error("Missing spaceKey for new page or pageId for existing page.");
      }
      navigate(`/spaces/${savedPage.space_key}/pages/${savedPage.id}`);

    } catch (err: any) { // Added type for err
      console.error('Failed to save page:', err);
      setError(`Failed to save page: ${err.message || 'Unknown error'}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <p>Loading editor...</p>;
  }

  if (error && !isSaving) { // Don't show page load error if a save error occurs
    // Allow user to still attempt to use editor if page load failed but it's a new page scenario
    if (!pageId && error.includes("Failed to load page content")) {
        // This is fine, indicates a new page
    } else {
        return <p style={{ color: 'red' }}>{error}</p>;
    }
  }


  return (
    <div style={{ padding: '20px' }}>
      {error && <p style={{ color: 'red', marginBottom: '10px' }}>{error}</p>}

      <div style={{ marginBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <input
            type="text" // Page Title Input
            value={pageTitle}
            onChange={(e) => setPageTitle(e.target.value)}
            placeholder="Page Title"
            style={{
              width: '70%', padding: '10px', fontSize: '1.2em',
              border: '1px solid #ccc', borderRadius: '4px'
            }}
        />
        <button onClick={toggleEditorMode} style={{ padding: '8px 12px'}}>
          {isMarkdownMode ? 'Switch to Rich Text' : 'Switch to Markdown'}
        </button>
      </div>

      {isMarkdownMode ? (
        <textarea
          value={markdownContent}
          onChange={handleMarkdownChange}
          placeholder="Enter Markdown content..."
          style={{ width: '100%', minHeight: '500px', border: '1px solid #ccc', padding: '10px', fontFamily: 'monospace' }}
        />
      ) : (
        <TiptapEditor
          content={editorContentJson}
          onChange={handleEditorChange}
          // pageTitle={pageTitle}
          // onTitleChange={setPageTitle} // TiptapEditor no longer manages title directly
        />
      )}

      <DrawioModal
        isOpen={isDrawioModalOpen && currentEditingDrawioNode !== null}
        onClose={handleDrawioModalClose}
        initialXml={currentEditingDrawioNode?.initialXml || ''}
        onSave={handleDrawioModalSave}
      />

      <button
        onClick={handleSave}
        disabled={isSaving || isLoading || !pageTitle.trim()}
        style={{ marginTop: '20px', padding: '10px 20px', fontSize: '1em', cursor: 'pointer' }}
      >
        {isSaving ? 'Saving...' : (pageId ? 'Save Changes' : 'Create Page')}
      </button>
      {spaceKey && pageId && (
         <button
            onClick={() => navigate(`/spaces/${spaceKey}/pages/${pageId}`)}
            style={{ marginTop: '20px', marginLeft:'10px', padding: '10px 20px', fontSize: '1em', cursor: 'pointer' }}
        >
        Cancel
        </button>
      )}
       {spaceKey && !pageId && (
         <button
            onClick={() => navigate(parentPageId ? `/spaces/${spaceKey}/pages/${parentPageId}` : `/spaces/${spaceKey}`)}
            style={{ marginTop: '20px', marginLeft:'10px', padding: '10px 20px', fontSize: '1em', cursor: 'pointer' }}
        >
        Cancel
        </button>
      )}
    </div>
  );
};

export default EditorView;
