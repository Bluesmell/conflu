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
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        disabled={!editor.can().chain().focus().toggleUnderline().run()}
        className={editor.isActive('underline') ? 'is-active' : ''}
      >
        Underline
      </button>
      <button
        onClick={() => editor.chain().focus().toggleStrike().run()}
        disabled={!editor.can().chain().focus().toggleStrike().run()}
        className={editor.isActive('strike') ? 'is-active' : ''}
      >
        Strike
      </button>
      <button
        onClick={() => editor.chain().focus().setParagraph().run()}
        className={editor.isActive('paragraph') ? 'is-active' : ''}
      >
        Paragraph
      </button>
      {[1, 2, 3, 4, 5, 6].map((level) => (
        <button
          key={level}
          onClick={() => editor.chain().focus().toggleHeading({ level: level as 1 | 2 | 3 | 4 | 5 | 6 }).run()}
          className={editor.isActive('heading', { level: level as 1 | 2 | 3 | 4 | 5 | 6 }) ? 'is-active' : ''}
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
      <button
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
        disabled={!editor.can().chain().focus().toggleBlockquote().run()}
        className={editor.isActive('blockquote') ? 'is-active' : ''}
      >
        Blockquote
      </button>
      <button
        onClick={() => editor.chain().focus().setHorizontalRule().run()}
        disabled={!editor.can().chain().focus().setHorizontalRule().run()}
      >
        HR
      </button>
      <button
        onClick={() => {
          const url = window.prompt('Enter Image URL:');
          if (url) {
            editor.chain().focus().setImage({ src: url }).run();
          }
        }}
        disabled={!editor.can().chain().focus().setImage({ src: '' }).run()}
      >
        Image
      </button>
      <button
        onClick={() => editor.chain().focus().toggleCodeBlock().run()}
        disabled={!editor.can().chain().focus().toggleCodeBlock().run()}
        className={editor.isActive('codeBlock') ? 'is-active' : ''}
      >
        Code Block
      </button>
      {editor.isActive('codeBlock') && (
        <select
            value={editor.getAttributes('codeBlock').language || ''}
            onChange={(e) => editor.chain().focus().setCodeBlock({ language: e.target.value }).run()}
            style={{ marginLeft: '5px', padding: '3px' }}
        >
            <option value="">auto</option>
            <option value="javascript">JavaScript</option>
            <option value="python">Python</option>
            <option value="html">HTML</option>
            <option value="css">CSS</option>
            <option value="typescript">TypeScript</option>
            <option value="java">Java</option>
            <option value="csharp">C#</option>
            <option value="php">PHP</option>
            <option value="ruby">Ruby</option>
            {/* Add more common languages */}
        </select>
      )}

      {/* Table Operations */}
      <button onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()}>
        Table
      </button>
      {editor.can().deleteTable() && <button onClick={() => editor.chain().focus().deleteTable().run()}>Del Table</button>}
      {editor.can().addColumnBefore() && <button onClick={() => editor.chain().focus().addColumnBefore().run()}>Add Col Before</button>}
      {editor.can().addColumnAfter() && <button onClick={() => editor.chain().focus().addColumnAfter().run()}>Add Col After</button>}
      {editor.can().deleteColumn() && <button onClick={() => editor.chain().focus().deleteColumn().run()}>Del Col</button>}
      {editor.can().addRowBefore() && <button onClick={() => editor.chain().focus().addRowBefore().run()}>Add Row Before</button>}
      {editor.can().addRowAfter() && <button onClick={() => editor.chain().focus().addRowAfter().run()}>Add Row After</button>}
      {editor.can().deleteRow() && <button onClick={() => editor.chain().focus().deleteRow().run()}>Del Row</button>}
      {editor.can().toggleHeaderCell() && <button onClick={() => editor.chain().focus().toggleHeaderCell().run()}>Toggle Header</button>}
      {/* Merge/Split cells might require more complex UI or specific conditions */}
      {/* {editor.can().mergeCells() && <button onClick={() => editor.chain().focus().mergeCells().run()}>Merge Cells</button>} */}
      {/* {editor.can().splitCell() && <button onClick={() => editor.chain().focus().splitCell().run()}>Split Cell</button>} */}


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
