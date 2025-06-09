import React from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
// import appSchema from '../../editor/schema'; // We will use StarterKit for simplicity first
import EditorToolbar from './EditorToolbar'; // Will be created next
import './TiptapEditor.css'; // We'll create this CSS file

interface TiptapEditorProps {
  content: string; // JSON string or HTML string (Tiptap handles both for initial content)
  onChange: (newContentJson: string, newContentHtml: string) => void;
  onTitleChange?: (newTitle: string) => void; // Optional: if title is managed on the same page
  pageTitle?: string; // Optional: if title is managed on the same page
}

const TiptapEditor: React.FC<TiptapEditorProps> = ({ content, onChange, pageTitle, onTitleChange }) => {
  let initialContent: any = content;
  try {
    // Attempt to parse if it's a JSON string, otherwise use as is (HTML string)
    initialContent = JSON.parse(content);
  } catch (e) {
    // If parsing fails, assume it's HTML or malformed JSON that Tiptap might handle
    // console.warn("Initial content is not a valid JSON string. Treating as HTML.", e);
  }

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Configure StarterKit, disable things not in our initial schema if necessary
        heading: {
          levels: [1, 2, 3],
        },
        // Ensure other StarterKit defaults are mostly fine for now
        // We want paragraph, text, bulletList, orderedList, listItem, bold, italic
        // StarterKit includes these.
        // blockquote: false, // Example: if we don't want blockquotes
        // hardBreak: false, // Example: if we don't want hard breaks
      }),
      Link.configure({
        openOnClick: false, // Don't open links when clicking in editor
        autolink: true,     // Automatically detect links as you type
        // HTMLAttributes: { // To ensure links open in new tab by default
        //   target: '_blank',
        //   rel: 'noopener noreferrer',
        // },
      }),
    ],
    content: initialContent, // Initial content
    onUpdate: ({ editor }) => {
      onChange(JSON.stringify(editor.getJSON()), editor.getHTML());
    },
    // Example of applying custom styling to the editor itself
    // editorProps: {
    //   attributes: {
    //     class: 'prose dark:prose-invert prose-sm sm:prose-base lg:prose-lg xl:prose-2xl p-4 focus:outline-none',
    //   },
    // },
  });

  if (!editor) {
    return <p>Loading editor...</p>;
  }

  return (
    <div className="tiptap-editor-container">
      {onTitleChange && typeof pageTitle === 'string' && (
        <input
          type="text"
          value={pageTitle}
          onChange={(e) => onTitleChange(e.target.value)}
          placeholder="Page Title"
          className="tiptap-editor-title-input"
        />
      )}
      <EditorToolbar editor={editor} />
      <EditorContent editor={editor} className="tiptap-editor-content" />
    </div>
  );
};

export default TiptapEditor;
