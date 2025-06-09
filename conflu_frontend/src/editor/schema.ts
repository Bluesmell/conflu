// Basic Tiptap schema
// Read more about schemas here: https://tiptap.dev/docs/editor/schema
// Note: This schema is for direct ProseMirror usage if needed.
// For Tiptap editor instances, you typically configure extensions directly.
// However, generateHTML can use a schema derived from extensions or a manually defined one.

import { Schema } from '@tiptap/pm/model';

const pDOM = ['p', 0] as const;
const blockquoteDOM = ['blockquote', 0] as const;
const hrDOM = ['hr'] as const;
const preDOM = ['pre', ['code', 0]] as const; // Code block with nested code tag
const brDOM = ['br'] as const;

export const appSchema = new Schema({
  nodes: {
    doc: {
      content: 'block+',
    },
    paragraph: {
      content: 'inline*',
      group: 'block',
      parseDOM: [{ tag: 'p' }],
      toDOM() { return pDOM; },
    },
    blockquote: {
      content: 'block+',
      group: 'block',
      defining: true,
      parseDOM: [{ tag: 'blockquote' }],
      toDOM() { return blockquoteDOM; },
    },
    horizontalRule: { // Corrected name to match Tiptap extension
      group: 'block',
      parseDOM: [{ tag: 'hr' }],
      toDOM() { return hrDOM; },
    },
    heading: {
      attrs: { level: { default: 1 } },
      content: 'inline*',
      group: 'block',
      defining: true,
      parseDOM: [
        { tag: 'h1', attrs: { level: 1 } },
        { tag: 'h2', attrs: { level: 2 } },
        { tag: 'h3', attrs: { level: 3 } },
        { tag: 'h4', attrs: { level: 4 } },
        { tag: 'h5', attrs: { level: 5 } },
        { tag: 'h6', attrs: { level: 6 } },
      ],
      toDOM(node) { return [`h${node.attrs.level}`, 0]; },
    },
    codeBlock: { // Corrected name
      content: 'text*', // Should primarily contain text
      marks: '', // No marks within code blocks typically
      group: 'block',
      code: true,
      defining: true,
      attrs: { language: { default: null } },
      parseDOM: [{ tag: 'pre', preserveWhitespace: 'full', getAttrs: dom => ({ language: (dom as HTMLElement).getAttribute('data-language') || null }) }],
      toDOM(node) {
        return ['pre', node.attrs.language ? { 'data-language': node.attrs.language, class: `language-${node.attrs.language}` } : {}, ['code', 0]];
      },
    },
    text: {
      group: 'inline',
    },
    image: {
      inline: false, // Images are typically block elements in this context, but can be inline too
      group: 'block', // Or inline, depending on desired behavior. Let's assume block for now.
      attrs: {
        src: { default: null },
        alt: { default: null },
        title: { default: null },
        align: { default: 'none' }, // 'none', 'left', 'center', 'right'
        width: { default: null },
        height: { default: null },
      },
      draggable: true,
      parseDOM: [{
        tag: 'img[src]',
        getAttrs: domNode => {
          const dom = domNode as HTMLElement;
          return {
            src: dom.getAttribute('src'),
            alt: dom.getAttribute('alt'),
            title: dom.getAttribute('title'),
            align: dom.getAttribute('data-align') || dom.style.float || (dom.style.display === 'block' && dom.style.marginLeft === 'auto' ? 'center' : 'none'),
            width: dom.getAttribute('width') || dom.style.width || null,
            height: dom.getAttribute('height') || dom.style.height || null,
          };
        },
      }],
      toDOM(node) {
        const { src, alt, title, align, width, height } = node.attrs;
        const attrs: any = { src, alt, title };
        if (width) attrs.width = width;
        if (height) attrs.height = height;

        let style = '';
        if (align === 'left') {
          attrs['data-align'] = 'left';
          // style = 'float: left; margin-right: 10px; margin-bottom: 10px;';
        } else if (align === 'right') {
          attrs['data-align'] = 'right';
          // style = 'float: right; margin-left: 10px; margin-bottom: 10px;';
        } else if (align === 'center') {
          attrs['data-align'] = 'center';
          // style = 'display: block; margin-left: auto; margin-right: auto; margin-bottom: 10px;';
        }
        // if (style) attrs.style = style; // Inline styles can be problematic, prefer classes or data-attrs

        // For centered images, a wrapper div might be better for styling if float is not used.
        // Tiptap's HTMLAttributes system on the extension is usually preferred for class/style manipulation.
        // This toDOM is a direct ProseMirror schema version.
        return ['img', attrs];
      },
    },
    hardBreak: { // Corrected name
      inline: true,
      group: 'inline',
      selectable: false,
      parseDOM: [{ tag: 'br' }],
      toDOM() { return brDOM; },
    },
    orderedList: {
      content: 'listItem+',
      group: 'block',
      attrs: { order: { default: 1 } },
      parseDOM: [{
        tag: 'ol',
        getAttrs: dom => ({
          order: (dom as HTMLElement).hasAttribute('start') ? parseInt((dom as HTMLElement).getAttribute('start') || '1', 10) : 1,
        }),
      }],
      toDOM(node) {
        return node.attrs.order === 1 ? ['ol', 0] : ['ol', { start: node.attrs.order }, 0];
      },
    },
    bulletList: { // Corrected name
      content: 'listItem+',
      group: 'block',
      parseDOM: [{ tag: 'ul' }],
      toDOM() { return ['ul', 0]; },
    },
    listItem: {
      content: 'paragraph block*', // Changed from 'block+' to allow paragraphs and other blocks. Tiptap default is 'paragraph (paragraph | block)*'
      defining: true, // Important for copy-paste and schema resolution
      parseDOM: [{ tag: 'li' }],
      toDOM() { return ['li', 0]; },
    },
    // Table related nodes
    table: {
        content: 'tableRow+',
        tableRole: 'table',
        isolating: true,
        group: 'block',
        parseDOM: [{tag: 'table'}],
        toDOM() { return ['table', ['tbody', 0]]; }, // Ensure tbody for structure
    },
    tableRow: {
        content: '(tableCell | tableHeader)+',
        tableRole: 'row',
        parseDOM: [{tag: 'tr'}],
        toDOM() { return ['tr', 0]; },
    },
    tableCell: {
        content: 'block+', // Allow block content within cells
        tableRole: 'cell',
        isolating: true,
        parseDOM: [{tag: 'td'}],
        toDOM() { return ['td', 0]; },
    },
    tableHeader: {
        content: 'block+',
        tableRole: 'header_cell',
        isolating: true,
        parseDOM: [{tag: 'th'}],
        toDOM() { return ['th', 0]; },
    },
    // FallbackMacroPlaceholder node
    fallbackMacroPlaceholder: {
      group: 'block',
      atom: true,
      attrs: {
        macroName: { default: 'Unknown Macro' },
        fallbackMacroId: { default: null },
      },
      draggable: true,
      toDOM: node => [
        'div',
        {
          'data-type': 'fallback-macro-placeholder',
          'data-macro-name': node.attrs.macroName,
          'data-fallback-id': String(node.attrs.fallbackMacroId),
          class: 'fallback-macro-node ProseMirror-widget',
        },
        `[Unsupported Macro: ${node.attrs.macroName}]`
      ],
      parseDOM: [
        {
          tag: 'div[data-type="fallback-macro-placeholder"]',
          getAttrs: dom => {
            const element = dom as HTMLElement;
            return {
              macroName: element.getAttribute('data-macro-name') || 'Unknown Macro',
              fallbackMacroId: parseInt(element.getAttribute('data-fallback-id') || '0', 10) || null,
            };
          },
        },
      ],
    },
    drawioDiagram: {
      group: 'block',
      atom: true,
      draggable: true,
      attrs: {
        xml: { default: '' },
        // placeholderId can be used to temporarily store a unique ID for the diagram
        // if it's created client-side and needs to be linked to an image preview before saving.
        // For Draw.io, the XML itself is the core data.
        // Previews are usually generated as SVGs or PNGs from the XML.
      },
      toDOM: node => [
        'div',
        {
          'data-type': 'drawio-diagram',
          // Store XML in a data attribute if it's not too large,
          // or rely on the NodeView to manage it and just render a placeholder here.
          // For simplicity in schema, often just a placeholder is rendered here.
          // The actual content (image preview) is handled by the NodeView.
          // 'data-xml': node.attrs.xml, // Potentially very large
        },
        // Fallback content for SSR or if NodeView doesn't load:
        '[Draw.io Diagram - Requires JavaScript to view and edit]'
      ],
      parseDOM: [
        {
          tag: 'div[data-type="drawio-diagram"]',
          getAttrs: domNode => {
            const dom = domNode as HTMLElement;
            // If XML was stored in a data attribute (not recommended for large XML):
            // const xml = dom.getAttribute('data-xml');
            // If XML is stored as text content inside a hidden <pre> tag (like Mermaid extension):
            const preElement = dom.querySelector('pre[data-drawio-xml]');
            const xml = preElement ? preElement.textContent : '';
            return { xml: xml || '' };
          },
        },
        // Optional: if Draw.io diagrams are saved as images with specific class/attributes
        // and XML is embedded in a data attribute on the image.
        // {
        //   tag: 'img[data-drawio-xml]',
        //   getAttrs: dom => ({ xml: (dom as HTMLElement).getAttribute('data-drawio-xml') })
        // }
      ],
    }
  },
  marks: {
    link: {
      attrs: {
        href: {},
        title: { default: null },
        target: { default: '_blank' }, // Default to open in new tab
      },
      inclusive: false,
      parseDOM: [{
        tag: 'a[href]',
        getAttrs: dom => ({
          href: (dom as HTMLElement).getAttribute('href'),
          title: (dom as HTMLElement).getAttribute('title'),
          target: (dom as HTMLElement).getAttribute('target'),
        }),
      }],
      toDOM(node) { return ['a', node.attrs, 0]; },
    },
    bold: {
      parseDOM: [
        { tag: 'strong' },
        { tag: 'b', getAttrs: node => (node as HTMLElement).style.fontWeight !== 'normal' && null },
        { style: 'font-weight', getAttrs: value => /^(bold(er)?|[5-9]\d{2,})$/.test(value as string) && null },
      ],
      toDOM() { return ['strong', 0]; },
    },
    italic: {
      parseDOM: [
        { tag: 'i' },
        { tag: 'em' },
        { style: 'font-style=italic' },
      ],
      toDOM() { return ['em', 0]; },
    },
    underline: { // Added
      parseDOM: [{tag: 'u'}, {style: 'text-decoration=underline'}],
      toDOM() { return ['u', 0]; },
    },
    strike: { // Added (strikethrough)
      parseDOM: [
        {tag: 's'}, {tag: 'del'}, {tag: 'strike'},
        {style: 'text-decoration=line-through'},
        {style: 'text-decoration-line=line-through'} // More specific CSS
      ],
      toDOM() { return ['s', 0]; }, // Using <s> for simplicity
    },
    code: { // Inline code
      parseDOM: [{ tag: 'code' }],
      toDOM() { return ['code', 0]; },
    },
  },
});

export default appSchema;
