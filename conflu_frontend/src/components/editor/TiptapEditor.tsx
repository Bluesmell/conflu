import React from 'react';
import { useEditor, EditorContent, Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

interface TiptapEditorProps {
  content: string; // Initial content (JSON string)
  onChange: (newContent: string) => void; // Callback for when content changes (as JSON string)
}

// Basic Toolbar Component
const MenuBar: React.FC<{ editor: Editor | null }> = ({ editor }) => {
  if (!editor) {
    return null;
  }

  return (
    <div style={{ border: '1px solid #ccc', padding: '5px', marginBottom: '5px', display: 'flex', flexWrap: 'wrap' }}>
      <button
        onClick={() => editor.chain().focus().toggleBold().run()}
        disabled={!editor.can().chain().focus().toggleBold().run()}
        className={editor.isActive('bold') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Bold
      </button>
      <button
        onClick={() => editor.chain().focus().toggleItalic().run()}
        disabled={!editor.can().chain().focus().toggleItalic().run()}
        className={editor.isActive('italic') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Italic
      </button>
      <button
        onClick={() => editor.chain().focus().toggleStrike().run()}
        disabled={!editor.can().chain().focus().toggleStrike().run()}
        className={editor.isActive('strike') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Strike
      </button>
      <button
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
        className={editor.isActive('heading', { level: 1 }) ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        H1
      </button>
      <button
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        className={editor.isActive('heading', { level: 2 }) ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        H2
      </button>
      <button
        onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        className={editor.isActive('heading', { level: 3 }) ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        H3
      </button>
      <button
        onClick={() => editor.chain().focus().setParagraph().run()}
        className={editor.isActive('paragraph') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Paragraph
      </button>
      <button
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={editor.isActive('bulletList') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Bullet List
      </button>
      <button
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={editor.isActive('orderedList') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Ordered List
      </button>
      <button
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        className={editor.isActive('blockquote') ? 'is-active' : ''}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Blockquote
      </button>
      <button
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Horizontal Rule
      </button>
      <button
        onClick={() => editor.chain().focus().undo().run()}
        disabled={!editor.can().undo()}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Undo
      </button>
      <button
        onClick={() => editor.chain().focus().redo().run()}
        disabled={!editor.can().redo()}
        style={{ marginRight: '5px', marginBottom: '5px' }}
      >
        Redo
      </button>
    </div>
  );
};


const TiptapEditor: React.FC<TiptapEditorProps> = ({ content, onChange }) => {
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // Configure StarterKit options:
        // heading: { levels: [1, 2, 3] }, // Already default
        // history: true, // Already default and enabled
        // You can disable extensions from StarterKit if needed:
        // codeBlock: false,
      }),
    ],
    content: JSON.parse(content), // Parse initial content string to JSON object for Tiptap
    onUpdate: ({ editor }) => {
      onChange(JSON.stringify(editor.getJSON())); // Output as JSON string
    },
  });

  return (
    <div>
      <MenuBar editor={editor} />
      <EditorContent editor={editor} style={{ border: '1px solid #ccc', padding: '10px', minHeight: '200px' }}/>
    </div>
  );
};

export default TiptapEditor;
