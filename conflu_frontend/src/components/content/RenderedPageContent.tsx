import React, { useMemo } from 'react';
import { generateHTML } from '@tiptap/core';
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

// For CodeBlockLowlight
import { lowlight } from 'lowlight'; // Use /core for smaller bundle if only registering some languages
import html from 'highlight.js/lib/languages/xml'; // XML for HTML
import css from 'highlight.js/lib/languages/css';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import java from 'highlight.js/lib/languages/java';
import csharp from 'highlight.js/lib/languages/csharp';
import cpp from 'highlight.js/lib/languages/cpp';
import php from 'highlight.js/lib/languages/php';
import ruby from 'highlight.js/lib/languages/ruby';
import go from 'highlight.js/lib/languages/go';
import rust from 'highlight.js/lib/languages/rust';
import sql from 'highlight.js/lib/languages/sql';
import yaml from 'highlight.js/lib/languages/yaml';
import json from 'highlight.js/lib/languages/json';
import bash from 'highlight.js/lib/languages/bash';
import shell from 'highlight.js/lib/languages/shell';
import makefile from 'highlight.js/lib/languages/makefile';
import dockerfile from 'highlight.js/lib/languages/dockerfile';


// Register languages for lowlight
lowlight.registerLanguage('html', html);
lowlight.registerLanguage('xml', html); // Alias for xml
lowlight.registerLanguage('css', css);
lowlight.registerLanguage('javascript', javascript);
lowlight.registerLanguage('js', javascript); // Alias
lowlight.registerLanguage('typescript', typescript);
lowlight.registerLanguage('ts', typescript); // Alias
lowlight.registerLanguage('python', python);
lowlight.registerLanguage('py', python); // Alias
lowlight.registerLanguage('java', java);
lowlight.registerLanguage('csharp', csharp);
lowlight.registerLanguage('cs', csharp); // Alias
lowlight.registerLanguage('cpp', cpp);
lowlight.registerLanguage('c++', cpp); // Alias
lowlight.registerLanguage('php', php);
lowlight.registerLanguage('ruby', ruby);
lowlight.registerLanguage('rb', ruby); // Alias
lowlight.registerLanguage('go', go);
lowlight.registerLanguage('rust', rust);
lowlight.registerLanguage('sql', sql);
lowlight.registerLanguage('yaml', yaml);
lowlight.registerLanguage('json', json);
lowlight.registerLanguage('bash', bash);
lowlight.registerLanguage('shell', shell); // Alias
lowlight.registerLanguage('makefile', makefile);
lowlight.registerLanguage('dockerfile', dockerfile);


// Styles for syntax highlighting (import one theme)
// Ensure this CSS file is available and linked in your project (e.g., in main.tsx or App.tsx)
// You might need to copy it from node_modules/highlight.js/styles/ to your public or src/assets folder
// For example: import '../../styles/highlightjs-theme-github-dark.css';
// Or if using a global stylesheet: @import 'highlight.js/styles/github-dark.css'; in your main CSS.
// For this example, we assume a theme is globally available or specifically imported elsewhere.


interface RenderedPageContentProps {
  rawContent: any; // ProseMirror JSON (can be string or object)
}

const RenderedPageContent: React.FC<RenderedPageContentProps> = ({ rawContent }) => {
  const html = useMemo(() => {
    if (!rawContent) {
      return '<p>No content available.</p>';
    }

    let parsedJson;
    if (typeof rawContent === 'string') {
      try {
        parsedJson = JSON.parse(rawContent);
      } catch (error) {
        console.error("Failed to parse rawContent JSON string:", error);
        return '<pre style="color: red;">Error: Could not parse page content.</pre>';
      }
    } else if (typeof rawContent === 'object' && rawContent !== null) {
      parsedJson = rawContent;
    } else {
      return '<pre style="color: orange;">Warning: Page content is not in a recognizable format.</pre>';
    }

    // Basic validation of document structure
    if (typeof parsedJson !== 'object' || parsedJson === null || parsedJson.type !== 'doc' || !Array.isArray(parsedJson.content)) {
        console.warn("Content does not appear to be a valid ProseMirror document:", parsedJson);
        return `<div style="color: orange"><p>Content may not be structured as expected.</p><pre>${JSON.stringify(parsedJson, null, 2)}</pre></div>`;
    }

    try {
      return generateHTML(parsedJson, [
        StarterKit.configure({
          // Configure StarterKit to disable elements handled by more specific extensions if needed
          // For example, if CodeBlockLowlight is used, disable StarterKit's codeBlock.
          codeBlock: false, // Use CodeBlockLowlight instead
          // Ensure other StarterKit defaults are fine, or specify them:
          // heading: { levels: [1, 2, 3, 4, 5, 6] },
          // horizontalRule: false, // Use specific HorizontalRule extension
          // blockquote: false, // Use specific Blockquote extension
        }),
        Image.configure({
            // inline: true, // If you want images to be inline by default
            // allowBase64: true, // If you need to support base64 images
        }),
        Table.configure({ resizable: true }), // Example configuration
        TableRow,
        TableHeader,
        TableCell,
        Underline,
        Strike,
        Blockquote,
        HorizontalRule,
        CodeBlockLowlight.configure({ lowlight }),
        Link.configure({
          // Ensure links open in new tab and add rel=noopener for security
          // These HTMLAttributes are applied to the rendered <a> tags.
          HTMLAttributes: {
            target: '_blank',
            rel: 'noopener noreferrer',
          },
          openOnClick: false, // Usually false for rendered content, true for editor
          autolink: true, // Detect links in text
        }),
        // Add any other extensions that match your schema and content
      ]);
    } catch (error) {
        console.error("Error generating HTML from ProseMirror JSON:", error);
        return '<pre style="color: red;">Error: Could not render page content.</pre>';
    }
  }, [rawContent]);

  // Render the HTML string.
  // Make sure to include necessary CSS for Tiptap content styling, e.g., .ProseMirror class styles.
  // And styles for syntax highlighting if not globally imported.
  return (
    <div
      className="prose-mirror-render tiptap-content" // Add a class for styling
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

export default RenderedPageContent;
