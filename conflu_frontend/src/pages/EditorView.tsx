import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import TiptapEditor from '../components/editor/TiptapEditor';
import { fetchPageDetails, createPage, updatePage } from '../services/api'; // Ensure createPage and updatePage are added to api.ts
import { Page } from '../types/apiModels'; // Ensure this type is appropriate

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
  const [editorContentHtml, setEditorContentHtml] = useState<string>(getEmptyDocHtml()); // Also store HTML for Tiptap
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [parentPageId, setParentPageId] = useState<string | null>(null);

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
          if (typeof data.raw_content === 'object') {
            setEditorContentJson(JSON.stringify(data.raw_content));
            // Tiptap doesn't directly take a JSON object for HTML conversion here,
            // so we'd need a way to get initial HTML or let Tiptap build it from JSON.
            // For now, we'll primarily work with JSON for consistency.
            // If backend provides HTML, that could be used too.
            // Let TiptapEditor derive HTML from the JSON content.
            setEditorContentHtml(''); // Let Tiptap generate from JSON
          } else if (typeof data.raw_content === 'string') {
            // Might be HTML or JSON string. TiptapEditor will attempt to parse JSON first.
            setEditorContentJson(data.raw_content); // Assume it's JSON for our backend
            setEditorContentHtml(''); // Let Tiptap generate from JSON
          } else {
             setEditorContentJson(getEmptyDocJson());
             setEditorContentHtml(getEmptyDocHtml());
          }
        })
        .catch(err => {
          console.error('Failed to load page:', err);
          setError('Failed to load page content. You might be creating a new page.');
          setEditorContentJson(getEmptyDocJson()); // Start with empty doc on error
          setEditorContentHtml(getEmptyDocHtml());
        })
        .finally(() => setIsLoading(false));
    } else { // New page
      setPageTitle('');
      setEditorContentJson(getEmptyDocJson());
      setEditorContentHtml(getEmptyDocHtml());
      setIsLoading(false);
    }
  }, [pageId]);

  const handleEditorChange = useCallback((newContentJson: string, newContentHtml: string) => {
    setEditorContentJson(newContentJson);
    setEditorContentHtml(newContentHtml); // We might not use this directly for saving if backend takes JSON
  }, []);

  const handleSave = async () => {
    if (!spaceKey && !pageId) { // spaceKey is needed for new pages, pageId for existing
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
      // raw_content should be the JSON object, so parse editorContentJson
      const contentToSave = JSON.parse(editorContentJson);

      if (pageId) { // Existing page
        savedPage = await updatePage(pageId, pageTitle, contentToSave);
        // navigate(`/spaces/${savedPage.space_key}/pages/${savedPage.id}`);
      } else if (spaceKey) { // New page
        savedPage = await createPage(spaceKey, pageTitle, contentToSave, parentPageId || undefined);
        // navigate(`/spaces/${savedPage.space_key}/pages/${savedPage.id}`);
      } else {
        throw new Error("Missing spaceKey for new page or pageId for existing page.");
      }
      // Navigate to the view page after save
      navigate(`/spaces/${savedPage.space_key}/pages/${savedPage.id}`);

    } catch (err) {
      console.error('Failed to save page:', err);
      setError('Failed to save page. Please try again.');
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
      {error && <p style={{ color: 'red' }}>{error}</p>}
      <TiptapEditor
        content={editorContentJson} // Pass JSON string, TiptapEditor handles parsing
        onChange={handleEditorChange}
        pageTitle={pageTitle}
        onTitleChange={setPageTitle}
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
