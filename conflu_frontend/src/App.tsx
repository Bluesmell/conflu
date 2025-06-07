import React, { useState } from 'react';
import TiptapEditor from './components/editor/TiptapEditor'; // Adjust path if needed
import './App.css'; // Or your main CSS file

// Initial empty document for Tiptap (ProseMirror JSON)
const initialEditorContentJson = JSON.stringify({
  type: 'doc',
  content: [
    {
      type: 'paragraph',
      content: [
        {
          type: 'text',
          text: 'Start typing here...',
        },
      ],
    },
  ],
});

function App() {
  const [pageTitle, setPageTitle] = useState('');
  // Store editor content as a JSON string, which is what our Page.raw_content expects
  const [editorContentJson, setEditorContentJson] = useState<string>(initialEditorContentJson);

  const handleSave = () => {
    console.log('Page Title:', pageTitle);
    try {
      const parsedContent = JSON.parse(editorContentJson); // Validate it's JSON
      console.log('Editor Content (JSON Object):', parsedContent);
      // Later, this will be sent to the backend API:
      // fetch('/api/pages/', {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json', /* Add Auth headers */ },
      //   body: JSON.stringify({ title: pageTitle, raw_content: parsedContent, space: 1 /* example space ID */ })
      // })
      alert('Page data logged to console. See developer tools.');
    } catch (error) {
      console.error("Error parsing editor content JSON:", error);
      alert("Error: Content is not valid JSON. Cannot save.");
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '800px', margin: '0 auto' }}>
      <h1>Create New Page</h1>
      <input
        type="text"
        value={pageTitle}
        onChange={(e) => setPageTitle(e.target.value)}
        placeholder="Page Title"
        style={{
          width: '100%',
          padding: '10px',
          marginBottom: '20px',
          fontSize: '1.2em',
          boxSizing: 'border-box'
        }}
      />
      <TiptapEditor
        content={editorContentJson} // Pass initial content JSON string
        onChange={(newJsonContent) => {
          setEditorContentJson(newJsonContent);
        }}
      />
      <button
        onClick={handleSave}
        style={{
          marginTop: '20px',
          padding: '10px 20px',
          fontSize: '1em',
          cursor: 'pointer'
        }}
      >
        Save Page (Log to Console)
      </button>
    </div>
  );
}

export default App;
