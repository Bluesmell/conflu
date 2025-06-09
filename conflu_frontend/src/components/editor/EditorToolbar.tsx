import React, { useCallback } from 'react';
import { Editor } from '@tiptap/react';
import './EditorToolbar.css'; // We'll create this CSS file

interface EditorToolbarProps {
  editor: Editor | null;
}

const EditorToolbar: React.FC<EditorToolbarProps> = ({ editor }) => {
  if (!editor) {
    return null;
  }

  const setLink = useCallback(() => {
    const previousUrl = editor.getAttributes('link').href;
    const url = window.prompt('URL', previousUrl);

    // cancelled
    if (url === null) {
      return;
    }

    // empty
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run();
      return;
    }

    // update link
    editor.chain().focus().extendMarkRange('link').setLink({ href: url, target: '_blank' }).run();
  }, [editor]);

  return (
    <div className="editor-toolbar">
      <button
        onClick={() => editor.chain().focus().toggleBold().run()}
        disabled={!editor.can().chain().focus().toggleBold().run()}
        className={editor.isActive('bold') ? 'is-active' : ''}
      >
        Bold
      </button>
      <button
        onClick={() => editor.chain().focus().toggleItalic().run()}
        disabled={!editor.can().chain().focus().toggleItalic().run()}
        className={editor.isActive('italic') ? 'is-active' : ''}
      >
        Italic
      </button>
      <button
        onClick={() => editor.chain().focus().setParagraph().run()}
        className={editor.isActive('paragraph') ? 'is-active' : ''}
      >
        Paragraph
      </button>
      {[1, 2, 3].map((level) => (
        <button
          key={level}
          onClick={() => editor.chain().focus().toggleHeading({ level: level as 1 | 2 | 3 }).run()}
          className={editor.isActive('heading', { level: level as 1 | 2 | 3 }) ? 'is-active' : ''}
        >
          H{level}
        </button>
      ))}
      <button
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={editor.isActive('bulletList') ? 'is-active' : ''}
      >
        Bullet List
      </button>
      <button
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={editor.isActive('orderedList') ? 'is-active' : ''}
      >
        Ordered List
      </button>
      <button onClick={setLink} className={editor.isActive('link') ? 'is-active' : ''}>
        Set Link
      </button>
      <button onClick={() => editor.chain().focus().unsetLink().run()} disabled={!editor.isActive('link')}>
        Unset Link
      </button>

      {/* Add more buttons as needed: undo, redo, etc. */}
      <button onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()}>
        Undo
      </button>
      <button onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()}>
        Redo
      </button>
    </div>
  );
};

export default EditorToolbar;
