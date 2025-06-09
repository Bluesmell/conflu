import React from 'react';
import { useEditor, EditorContent } from '@tiptap/react'; // Removed Editor type, not directly used by component itself
import StarterKit from '@tiptap/starter-kit';
import Link from '@tiptap/extension-link';
import Image from '@tiptap/extension-image';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import Underline from '@tiptap/extension-underline';
import Strike from '@tiptap/extension-strike';
import Blockquote from '@tiptap/extension-blockquote';
import HorizontalRule from '@tiptap/extension-horizontal-rule';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';

// For CodeBlockLowlight - import lowlight and languages as in RenderedPageContent
import { lowlight } from 'lowlight/lib/core';
import html from 'highlight.js/lib/languages/xml';
import css from 'highlight.js/lib/languages/css';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
// Add more languages as needed and register them below

import EditorToolbar from './EditorToolbar';
import './TiptapEditor.css';

// Register languages for lowlight
lowlight.registerLanguage('html', html);
lowlight.registerLanguage('xml', html);
lowlight.registerLanguage('css', css);
lowlight.registerLanguage('javascript', javascript);
lowlight.registerLanguage('js', javascript);
lowlight.registerLanguage('typescript', typescript);
lowlight.registerLanguage('ts', typescript);
lowlight.registerLanguage('python', python);
lowlight.registerLanguage('py', python);
// Register other languages imported above (java, csharp, etc.) if they were copied

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
        heading: {
          levels: [1, 2, 3, 4, 5, 6], // All heading levels
        },
        // Disable StarterKit's versions if we are using more specific ones
        // or want different configurations.
        codeBlock: false, // Using CodeBlockLowlight instead
        // blockquote: false, // Using Blockquote extension below
        // horizontalRule: false, // Using HorizontalRule extension below
        // Other StarterKit defaults like paragraph, bold, italic, lists are fine.
      }),
      Link.configure({
        openOnClick: true, // For editor, allow opening link on click
        autolink: true,
        HTMLAttributes: {
          target: '_blank',
          rel: 'noopener noreferrer',
        },
      }),
      Image.configure({
        // inline: false, // Default is false (block image)
        // allowBase64: false, // Default is false
      }),
      Table.configure({
        resizable: true,
      }),
      TableRow,
      TableHeader,
      TableCell,
      Underline,
      Strike,
      Blockquote, // Use the specific extension
      HorizontalRule, // Use the specific extension
      CodeBlockLowlight.configure({
        lowlight,
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
